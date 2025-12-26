# Copyright 2024-2025 ELEVAI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Amazon Connect Storage Configuration

Handles S3 bucket associations and Firehose setup for Connect instances.
"""

from typing import Dict
import pulumi
import pulumi_aws as aws

from ..utils.naming import create_name, create_logical_name


def associate_s3_buckets(
    connect_instance: aws.connect.Instance,
    s3_buckets: Dict[str, aws.s3.Bucket],
    kms_key: aws.kms.Key
) -> None:
    """
    Associate S3 buckets with Amazon Connect for different storage types.
    
    Supported bucket types:
    - recordings: Call recordings
    - chat_transcripts: Chat transcripts
    - exported_reports: Scheduled reports
    - attachments: File attachments
    - screen_recordings: Screen recordings
    - contact_evaluations: Contact evaluations
    - email_messages: Email messages
    
    Args:
        connect_instance: The Amazon Connect instance
        s3_buckets: Dictionary of S3 buckets to associate
        kms_key: KMS key for data encryption
    """
    bucket_configs = [
        ("recordings", "CALL_RECORDINGS", "call-recordings"),
        ("chat_transcripts", "CHAT_TRANSCRIPTS", "chat-transcripts"),
        ("exported_reports", "SCHEDULED_REPORTS", "exported-reports"),
        ("attachments", "ATTACHMENTS", "attachments"),
        ("screen_recordings", "SCREEN_RECORDINGS", "screen-recordings"),
        ("contact_evaluations", "CONTACT_EVALUATIONS", "contact-evaluations"),
        ("email_messages", "EMAIL_MESSAGES", "email-messages"),
    ]
    
    for bucket_key, resource_type, purpose in bucket_configs:
        if bucket_key in s3_buckets:
            _associate_bucket(
                connect_instance, 
                s3_buckets[bucket_key], 
                kms_key, 
                resource_type, 
                purpose
            )


def _associate_bucket(
    connect_instance: aws.connect.Instance,
    bucket: aws.s3.Bucket,
    kms_key: aws.kms.Key,
    resource_type: str,
    purpose: str
) -> None:
    """
    Create storage configuration for a single bucket type.
    """
    logical_name = create_logical_name("connect", f"{purpose}-storage")
    
    aws.connect.InstanceStorageConfig(
        logical_name,
        instance_id=connect_instance.id,
        resource_type=resource_type,
        storage_config=aws.connect.InstanceStorageConfigStorageConfigArgs(
            storage_type="S3",
            s3_config=aws.connect.InstanceStorageConfigStorageConfigS3ConfigArgs(
                bucket_name=bucket.id,
                bucket_prefix=purpose,
                encryption_config=aws.connect.InstanceStorageConfigStorageConfigS3ConfigEncryptionConfigArgs(
                    encryption_type="KMS",
                    key_id=kms_key.arn,
                ),
            ),
        ),
        opts=pulumi.ResourceOptions(depends_on=[connect_instance])
    )


def create_contact_flow_logs_firehose(
    tags: Dict[str, str], 
    kms_key: aws.kms.Key, 
    logging_bucket: aws.s3.Bucket
) -> tuple[aws.kinesis.FirehoseDeliveryStream, aws.s3.Bucket]:
    """
    Create Kinesis Firehose for contact flow logs.
    
    Creates:
    - S3 bucket with versioning and encryption
    - IAM role for Firehose
    - Firehose delivery stream
    
    Args:
        tags: Tags to apply to resources
        kms_key: KMS key for data encryption
        logging_bucket: S3 bucket for access logs
        
    Returns:
        Tuple of (Firehose delivery stream, S3 bucket)
    """
    log_bucket = _create_firehose_bucket(tags, kms_key, logging_bucket)
    
    firehose_role = _create_firehose_role(tags)
    
    _attach_firehose_policy(firehose_role, log_bucket)
    
    firehose_name = create_name("kfs", "contact-records")
    firehose_logical = create_logical_name("kfs", "contact-records")
    
    firehose = aws.kinesis.FirehoseDeliveryStream(
        firehose_logical,
        name=firehose_name,
        destination="extended_s3",
        extended_s3_configuration=aws.kinesis.FirehoseDeliveryStreamExtendedS3ConfigurationArgs(
            role_arn=firehose_role.arn,
            bucket_arn=log_bucket.arn,
            prefix="contact-records/",
            error_output_prefix="errors/",
            buffering_size=5,
            buffering_interval=300,
        ),
        server_side_encryption=aws.kinesis.FirehoseDeliveryStreamServerSideEncryptionArgs(
            enabled=True,
            key_type="CUSTOMER_MANAGED_CMK",
            key_arn=kms_key.arn,
        ),
        tags={**tags, "Name": firehose_name},
        opts=pulumi.ResourceOptions(depends_on=[firehose_role, log_bucket, kms_key])
    )
    
    return firehose, log_bucket


def _create_firehose_bucket(
    tags: Dict[str, str], 
    kms_key: aws.kms.Key, 
    logging_bucket: aws.s3.Bucket
) -> aws.s3.Bucket:
    """
    Create and configure S3 bucket for Firehose logs.
    """
    bucket_logical = create_logical_name("s3", "contact-records")
    
    log_bucket = aws.s3.Bucket(
        bucket_logical,
        object_lock_enabled=True,
        tags={**tags, "Purpose": "ContactFlowLogs"}
    )
    
    aws.s3.BucketVersioning(
        f"{bucket_logical}-versioning",
        bucket=log_bucket.id,
        versioning_configuration=aws.s3.BucketVersioningVersioningConfigurationArgs(
            status="Enabled",
        )
    )
    
    aws.s3.BucketServerSideEncryptionConfiguration(
        f"{bucket_logical}-encryption",
        bucket=log_bucket.id,
        rules=[
            aws.s3.BucketServerSideEncryptionConfigurationRuleArgs(
                apply_server_side_encryption_by_default=aws.s3.BucketServerSideEncryptionConfigurationRuleApplyServerSideEncryptionByDefaultArgs(
                    sse_algorithm="aws:kms",
                    kms_master_key_id=kms_key.arn,
                ),
                bucket_key_enabled=True,
            )
        ]
    )
    
    aws.s3.BucketPublicAccessBlock(
        f"{bucket_logical}-public-access-block",
        bucket=log_bucket.id,
        block_public_acls=True,
        block_public_policy=True,
        ignore_public_acls=True,
        restrict_public_buckets=True
    )
    
    log_bucket_ssl_policy = log_bucket.arn.apply(
        lambda arn: aws.iam.get_policy_document(
            statements=[
                aws.iam.GetPolicyDocumentStatementArgs(
                    sid="RequireSSL",
                    effect="Deny",
                    principals=[
                        aws.iam.GetPolicyDocumentStatementPrincipalArgs(
                            type="*",
                            identifiers=["*"],
                        )
                    ],
                    actions=["s3:*"],
                    resources=[
                        arn,
                        f"{arn}/*",
                    ],
                    conditions=[
                        aws.iam.GetPolicyDocumentStatementConditionArgs(
                            test="Bool",
                            variable="aws:SecureTransport",
                            values=["false"],
                        )
                    ],
                )
            ]
        ).json
    )
    
    aws.s3.BucketPolicy(
        f"{bucket_logical}-ssl-policy",
        bucket=log_bucket.id,
        policy=log_bucket_ssl_policy
    )
    
    config = pulumi.Config("s3")
    contact_records_archive_days = config.get_int("contactRecords.archiveDays") or config.get_int("archiveDays") or 90
    contact_records_deletion_days = config.get_int("contactRecords.deletionDays") or config.get_int("deletionDays") or 365
    
    aws.s3.BucketLifecycleConfiguration(
        f"{bucket_logical}-lifecycle",
        bucket=log_bucket.id,
        rules=[
            aws.s3.BucketLifecycleConfigurationRuleArgs(
                id="archive-and-expire",
                status="Enabled",
                transitions=[
                    aws.s3.BucketLifecycleConfigurationRuleTransitionArgs(
                        days=contact_records_archive_days,
                        storage_class="STANDARD_IA",
                    ),
                ],
                expiration=aws.s3.BucketLifecycleConfigurationRuleExpirationArgs(
                    days=contact_records_deletion_days,
                ),
            )
        ]
    )
    
    aws.s3.BucketLogging(
        f"{bucket_logical}-logging",
        bucket=log_bucket.id,
        target_bucket=logging_bucket.id,
        target_prefix="contact-records/"
    )
    
    return log_bucket


def _create_firehose_role(tags: Dict[str, str]) -> aws.iam.Role:
    """
    Create IAM role for Firehose.
    """
    firehose_assume_role_policy = aws.iam.get_policy_document(
        statements=[
            aws.iam.GetPolicyDocumentStatementArgs(
                actions=["sts:AssumeRole"],
                principals=[
                    aws.iam.GetPolicyDocumentStatementPrincipalArgs(
                        type="Service",
                        identifiers=["firehose.amazonaws.com"],
                    )
                ],
            )
        ]
    )
    
    role_name = create_name("iam-role", "firehose-delivery")
    role_logical = create_logical_name("iam-role", "firehose-delivery")
    
    firehose_role = aws.iam.Role(
        role_logical,
        name=role_name,
        assume_role_policy=firehose_assume_role_policy.json,
        tags={**tags, "Name": role_name}
    )
    
    return firehose_role


def _attach_firehose_policy(
    role: aws.iam.Role, 
    bucket: aws.s3.Bucket
) -> None:
    """
    Attach S3 access policy to Firehose role.
    """
    firehose_policy = bucket.arn.apply(
        lambda bucket_arn: aws.iam.get_policy_document(
            statements=[
                aws.iam.GetPolicyDocumentStatementArgs(
                    actions=[
                        "s3:PutObject",
                        "s3:GetObject",
                        "s3:ListBucket",
                    ],
                    resources=[
                        f"{bucket_arn}/*",
                        bucket_arn,
                    ],
                )
            ]
        ).json
    )
    
    policy_logical = create_logical_name("iam-policy", "firehose-s3-access")
    
    aws.iam.RolePolicy(
        policy_logical,
        role=role.id,
        policy=firehose_policy
    )
