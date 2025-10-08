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
S3 Buckets

Creates S3 buckets for recordings, reports, and data exports.
"""

from typing import Dict, Optional
import pulumi
import pulumi_aws as aws
import json


def create_logging_bucket(resource_name: str, tags: Dict[str, str], kms_key: aws.kms.Key) -> aws.s3.Bucket:
    """
    Create a dedicated S3 bucket for storing access logs from all other buckets.
    
    This bucket stores server access logs for all Amazon Connect S3 buckets.
    Per AWS best practice, this bucket does NOT have logging enabled on itself
    to avoid infinite logging loops. Suppress the security finding for this bucket.
    
    Args:
        resource_name: Pulumi resource name
        tags: Tags to apply to the bucket
        kms_key: KMS key for bucket encryption
        
    Returns:
        S3 bucket for access logs
    """
    
    # Create the logging bucket with Object Lock enabled
    bucket = aws.s3.Bucket(
        resource_name,
        object_lock_enabled=True,
        tags={**tags, "Purpose": "AccessLogs"},
    )
    
    # Enable versioning for audit trail
    aws.s3.BucketVersioning(
        f"{resource_name}-versioning",
        bucket=bucket.id,
        versioning_configuration=aws.s3.BucketVersioningVersioningConfigurationArgs(
            status="Enabled",
        ),
    )
    
    # Enable KMS encryption using customer-managed key
    aws.s3.BucketServerSideEncryptionConfiguration(
        f"{resource_name}-encryption",
        bucket=bucket.id,
        rules=[
            aws.s3.BucketServerSideEncryptionConfigurationRuleArgs(
                apply_server_side_encryption_by_default=aws.s3.BucketServerSideEncryptionConfigurationRuleApplyServerSideEncryptionByDefaultArgs(
                    sse_algorithm="aws:kms",
                    kms_master_key_id=kms_key.arn,
                ),
                bucket_key_enabled=True,
            )
        ],
    )
    
    # Block public access
    aws.s3.BucketPublicAccessBlock(
        f"{resource_name}-public-access-block",
        bucket=bucket.id,
        block_public_acls=True,
        block_public_policy=True,
        ignore_public_acls=True,
        restrict_public_buckets=True,
    )
    
    # Get current AWS account and region for bucket policy
    current = aws.get_caller_identity()
    region = aws.get_region()
    
    # Bucket policy to allow S3 service to write logs and require SSL
    bucket_policy = aws.s3.BucketPolicy(
        f"{resource_name}-policy",
        bucket=bucket.id,
        policy=pulumi.Output.all(
            bucket.arn,
            current.account_id,
            region.id
        ).apply(
            lambda args: json.dumps({
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "S3ServerAccessLogsPolicy",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "logging.s3.amazonaws.com"
                        },
                        "Action": "s3:PutObject",
                        "Resource": f"{args[0]}/*",
                        "Condition": {
                            "StringEquals": {
                                "aws:SourceAccount": args[1]
                            }
                        }
                    },
                    {
                        "Sid": "RequireSSL",
                        "Effect": "Deny",
                        "Principal": "*",
                        "Action": "s3:*",
                        "Resource": [
                            args[0],
                            f"{args[0]}/*"
                        ],
                        "Condition": {
                            "Bool": {
                                "aws:SecureTransport": "false"
                            }
                        }
                    }
                ]
            })
        ),
    )
    
    # Lifecycle rule to expire old logs
    aws.s3.BucketLifecycleConfiguration(
        f"{resource_name}-lifecycle",
        bucket=bucket.id,
        rules=[
            aws.s3.BucketLifecycleConfigurationRuleArgs(
                id="expire-logs",
                status="Enabled",
                transitions=[
                    aws.s3.BucketLifecycleConfigurationRuleTransitionArgs(
                        days=90,
                        storage_class="STANDARD_IA",
                    ),
                ],
                expiration=aws.s3.BucketLifecycleConfigurationRuleExpirationArgs(
                    days=365,
                ),
                noncurrent_version_expiration=aws.s3.BucketLifecycleConfigurationRuleNoncurrentVersionExpirationArgs(
                    noncurrent_days=90,
                ),
            )
        ],
    )
    
    return bucket


def get_retention_config(config: pulumi.Config, bucket_type: str, default_archive: int, default_deletion: int) -> tuple[int, int]:
    """
    Get retention configuration for a specific bucket type, with fallback to defaults.
    
    Args:
        config: Pulumi config object
        bucket_type: Type of bucket (e.g., "recordings", "chatTranscripts")
        default_archive: Default archive days
        default_deletion: Default deletion days
        
    Returns:
        Tuple of (archive_days, deletion_days)
    """
    # Try to get bucket-specific config, fall back to defaults
    archive_key = f"{bucket_type}.archiveDays"
    deletion_key = f"{bucket_type}.deletionDays"
    
    archive_days = config.get_int(archive_key)
    if archive_days is None:
        archive_days = default_archive
    
    deletion_days = config.get_int(deletion_key)
    if deletion_days is None:
        deletion_days = default_deletion
    
    return archive_days, deletion_days


def create_s3_buckets(tags: Dict[str, str], kms_key: aws.kms.Key) -> Dict[str, aws.s3.Bucket]:
    """
    Create S3 buckets for Amazon Connect data storage.
    
    Args:
        tags: Tags to apply to all buckets
        kms_key: KMS key for bucket encryption
        
    Returns:
        Dictionary of bucket names to bucket resources
    """
    config = pulumi.Config("s3")
    
    # Get default retention configuration
    default_archive_days = config.get_int("archiveDays") or 90
    default_deletion_days = config.get_int("deletionDays") or 365
    
    # Create dedicated logging bucket (receives logs from all other buckets)
    logging_bucket = create_logging_bucket("s3-access-logs", tags, kms_key)
    
    buckets = {}
    
    # Call Recordings bucket - stores call recordings
    archive_days, deletion_days = get_retention_config(config, "recordings", default_archive_days, default_deletion_days)
    recordings_bucket = create_secure_bucket(
        "call-recordings",
        "CallRecordings",
        tags,
        archive_days,
        deletion_days,
        kms_key,
        logging_bucket
    )
    buckets["recordings"] = recordings_bucket
    
    # Chat transcripts bucket - stores chat transcripts
    archive_days, deletion_days = get_retention_config(config, "chatTranscripts", default_archive_days, default_deletion_days)
    chat_transcripts_bucket = create_secure_bucket(
        "chat-transcripts",
        "ChatTranscripts",
        tags,
        archive_days,
        deletion_days,
        kms_key,
        logging_bucket
    )
    buckets["chat_transcripts"] = chat_transcripts_bucket
    
    # Exported reports bucket - stores exported reports
    archive_days, deletion_days = get_retention_config(config, "exportedReports", default_archive_days, default_deletion_days)
    exported_reports_bucket = create_secure_bucket(
        "exported-reports",
        "ExportedReports",
        tags,
        archive_days,
        deletion_days,
        kms_key,
        logging_bucket
    )
    buckets["exported_reports"] = exported_reports_bucket
    
    # Attachments bucket - stores contact attachments
    archive_days, deletion_days = get_retention_config(config, "attachments", default_archive_days, default_deletion_days)
    attachments_bucket = create_secure_bucket(
        "attachments",
        "Attachments",
        tags,
        archive_days,
        deletion_days,
        kms_key,
        logging_bucket
    )
    buckets["attachments"] = attachments_bucket
    
    # Screen Recordings bucket - stores screen recordings
    archive_days, deletion_days = get_retention_config(config, "screenRecordings", default_archive_days, default_deletion_days)
    screen_recordings_bucket = create_secure_bucket(
        "screen-recordings",
        "ScreenRecordings",
        tags,
        archive_days,
        deletion_days,
        kms_key,
        logging_bucket
    )
    buckets["screen_recordings"] = screen_recordings_bucket
    
    # Contact Evaluations bucket - stores contact evaluations
    archive_days, deletion_days = get_retention_config(config, "contactEvaluations", default_archive_days, default_deletion_days)
    contact_evaluations_bucket = create_secure_bucket(
        "contact-evaluations",
        "ContactEvaluations",
        tags,
        archive_days,
        deletion_days,
        kms_key,
        logging_bucket
    )
    buckets["contact_evaluations"] = contact_evaluations_bucket
    
    # Email Messages bucket - stores email messages
    archive_days, deletion_days = get_retention_config(config, "emailMessages", default_archive_days, default_deletion_days)
    email_messages_bucket = create_secure_bucket(
        "email-messages",
        "EmailMessages",
        tags,
        archive_days,
        deletion_days,
        kms_key,
        logging_bucket
    )
    buckets["email_messages"] = email_messages_bucket
    
    # Add logging bucket to exports
    buckets["logging"] = logging_bucket
    
    return buckets


def create_secure_bucket(
    resource_name: str,
    purpose: str,
    tags: Dict[str, str],
    archive_days: int,
    deletion_days: int,
    kms_key: aws.kms.Key,
    logging_bucket: aws.s3.Bucket
) -> aws.s3.Bucket:
    """
    Create a secure S3 bucket with KMS encryption, versioning, and lifecycle policies.
    
    Args:
        resource_name: Pulumi resource name
        purpose: Purpose of the bucket (for tagging)
        tags: Additional tags
        archive_days: Days before transitioning to IA storage
        deletion_days: Days before object expiration/deletion
        kms_key: KMS key for bucket encryption
        
    Returns:
        S3 bucket resource
    """
    
    # Create bucket with Object Lock enabled
    bucket = aws.s3.Bucket(
        resource_name,
        object_lock_enabled=True,
        tags={**tags, "Purpose": purpose},
    )
    
    # Enable versioning
    aws.s3.BucketVersioning(
        f"{resource_name}-versioning",
        bucket=bucket.id,
        versioning_configuration=aws.s3.BucketVersioningVersioningConfigurationArgs(
            status="Enabled",
        ),
    )
    
    # Enable KMS encryption using customer-managed key
    aws.s3.BucketServerSideEncryptionConfiguration(
        f"{resource_name}-encryption",
        bucket=bucket.id,
        rules=[
            aws.s3.BucketServerSideEncryptionConfigurationRuleArgs(
                apply_server_side_encryption_by_default=aws.s3.BucketServerSideEncryptionConfigurationRuleApplyServerSideEncryptionByDefaultArgs(
                    sse_algorithm="aws:kms",
                    kms_master_key_id=kms_key.arn,
                ),
                bucket_key_enabled=True,
            )
        ],
    )
    
    # Block public access
    aws.s3.BucketPublicAccessBlock(
        f"{resource_name}-public-access-block",
        bucket=bucket.id,
        block_public_acls=True,
        block_public_policy=True,
        ignore_public_acls=True,
        restrict_public_buckets=True,
    )
    
    # Require SSL/TLS for all requests
    ssl_policy = bucket.arn.apply(
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
        f"{resource_name}-ssl-policy",
        bucket=bucket.id,
        policy=ssl_policy,
    )
    
    # Add lifecycle rule with configurable retention
    lifecycle_rules = [
        aws.s3.BucketLifecycleConfigurationRuleArgs(
            id="archive-and-expire",
            status="Enabled",
            transitions=[
                aws.s3.BucketLifecycleConfigurationRuleTransitionArgs(
                    days=archive_days,
                    storage_class="STANDARD_IA",
                ),
            ],
            expiration=aws.s3.BucketLifecycleConfigurationRuleExpirationArgs(
                days=deletion_days,
            ),
        )
    ]
    
    aws.s3.BucketLifecycleConfiguration(
        f"{resource_name}-lifecycle",
        bucket=bucket.id,
        rules=lifecycle_rules,
    )
    
    # Enable server access logging
    aws.s3.BucketLogging(
        f"{resource_name}-logging",
        bucket=bucket.id,
        target_bucket=logging_bucket.id,
        target_prefix=f"{resource_name}/",
    )
    
    return bucket
