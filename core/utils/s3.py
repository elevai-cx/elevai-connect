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
S3 Utilities

Reusable S3 bucket creation functions with security best practices.
"""

from typing import Dict, Optional
import json
import pulumi
import pulumi_aws as aws


def create_logging_bucket(
    resource_name: str, 
    tags: Dict[str, str], 
    kms_key: aws.kms.Key,
    bucket_name: Optional[str] = None
) -> aws.s3.Bucket:
    """
    Create a dedicated S3 bucket for storing access logs.
    
    This bucket stores server access logs for other buckets.
    Per AWS best practice, this bucket does NOT have logging enabled on itself.
    
    Args:
        resource_name: Pulumi resource name
        tags: Tags to apply to the bucket
        kms_key: KMS key for bucket encryption
        bucket_name: Optional physical bucket name (if not provided, AWS auto-generates)
        
    Returns:
        S3 bucket for access logs
    """
    bucket_args = {
        "object_lock_enabled": True,
        "tags": {**tags, "Purpose": "AccessLogs"},
    }
    if bucket_name:
        bucket_args["bucket"] = bucket_name

    bucket = aws.s3.Bucket(
        resource_name,
        opts=pulumi.ResourceOptions(retain_on_delete=True),
        **bucket_args,
    )
    
    aws.s3.BucketVersioning(
        f"{resource_name}-versioning",
        bucket=bucket.id,
        versioning_configuration=aws.s3.BucketVersioningVersioningConfigurationArgs(
            status="Enabled",
        )
    )
    
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
        ]
    )
    
    aws.s3.BucketPublicAccessBlock(
        f"{resource_name}-public-access-block",
        bucket=bucket.id,
        block_public_acls=True,
        block_public_policy=True,
        ignore_public_acls=True,
        restrict_public_buckets=True
    )
    
    current = aws.get_caller_identity()
    region = aws.get_region()
    
    aws.s3.BucketPolicy(
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
                        "Principal": {"Service": "logging.s3.amazonaws.com"},
                        "Action": "s3:PutObject",
                        "Resource": f"{args[0]}/*",
                        "Condition": {
                            "StringEquals": {"aws:SourceAccount": args[1]}
                        }
                    },
                    {
                        "Sid": "RequireSSL",
                        "Effect": "Deny",
                        "Principal": "*",
                        "Action": "s3:*",
                        "Resource": [args[0], f"{args[0]}/*"],
                        "Condition": {
                            "Bool": {"aws:SecureTransport": "false"}
                        }
                    }
                ]
            })
        )
    )
    
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
        ]
    )
    
    return bucket


def create_secure_s3_bucket(
    resource_name: str,
    purpose: str,
    tags: Dict[str, str],
    kms_key: aws.kms.Key,
    logging_bucket: Optional[aws.s3.Bucket] = None,
    archive_days: int = 90,
    deletion_days: int = 365,
    enable_object_lock: bool = True,
    additional_policy_statements: Optional[list] = None,
    lifecycle_rules: Optional[list] = None,
    bucket_name: Optional[str] = None,
) -> aws.s3.Bucket:
    """
    Create a secure S3 bucket with encryption, versioning, and lifecycle policies.
    
    This is a reusable utility that applies AWS security best practices:
    - KMS encryption
    - Versioning enabled
    - Public access blocked
    - SSL/TLS required
    - Lifecycle policies for cost optimization
    - Optional access logging
    
    Args:
        resource_name: Pulumi resource name
        purpose: Purpose of the bucket (for tagging)
        tags: Additional tags
        kms_key: KMS key for bucket encryption
        logging_bucket: Optional bucket for access logs
        archive_days: Days before transitioning to IA storage (default: 90)
        deletion_days: Days before object expiration (default: 365)
        enable_object_lock: Enable Object Lock (default: True)
        additional_policy_statements: Optional additional bucket policy statements
        lifecycle_rules: Optional custom lifecycle rules (overrides archive/deletion)
        bucket_name: Optional physical bucket name (if not provided, AWS auto-generates)
        
    Returns:
        S3 bucket resource
    """
    bucket_args = {
        "object_lock_enabled": enable_object_lock,
        "tags": {**tags, "Purpose": purpose},
    }
    if bucket_name:
        bucket_args["bucket"] = bucket_name

    bucket = aws.s3.Bucket(
        resource_name,
        opts=pulumi.ResourceOptions(retain_on_delete=True),
        **bucket_args,
    )
    
    aws.s3.BucketVersioning(
        f"{resource_name}-versioning",
        bucket=bucket.id,
        versioning_configuration=aws.s3.BucketVersioningVersioningConfigurationArgs(
            status="Enabled",
        )
    )
    
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
        ]
    )
    
    aws.s3.BucketPublicAccessBlock(
        f"{resource_name}-public-access-block",
        bucket=bucket.id,
        block_public_acls=True,
        block_public_policy=True,
        ignore_public_acls=True,
        restrict_public_buckets=True
    )
    
    # Build bucket policy statements
    def build_policy(arn: str) -> str:
        statements = [
            {
                "Sid": "RequireSSL",
                "Effect": "Deny",
                "Principal": "*",
                "Action": "s3:*",
                "Resource": [arn, f"{arn}/*"],
                "Condition": {
                    "Bool": {"aws:SecureTransport": "false"}
                }
            }
        ]

        if additional_policy_statements:
            # Replace the wildcard resource sentinel with the real bucket ARN
            # so callers can pass statements without knowing the bucket name.
            resolved = []
            for stmt in additional_policy_statements:
                s = dict(stmt)
                resource = s.get("Resource")
                if resource == "arn:aws:s3:::*/*":
                    s["Resource"] = f"{arn}/*"
                elif resource == "arn:aws:s3:::*":
                    s["Resource"] = arn
                resolved.append(s)
            statements.extend(resolved)

        return json.dumps({
            "Version": "2012-10-17",
            "Statement": statements
        })
    
    aws.s3.BucketPolicy(
        f"{resource_name}-policy",
        bucket=bucket.id,
        policy=bucket.arn.apply(build_policy)
    )
    
    # Apply lifecycle rules
    if lifecycle_rules:
        rules = lifecycle_rules
    else:
        rules = [
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
        rules=rules
    )
    
    # Enable access logging if logging bucket provided
    if logging_bucket:
        aws.s3.BucketLogging(
            f"{resource_name}-logging",
            bucket=bucket.id,
            target_bucket=logging_bucket.id,
            target_prefix=f"{resource_name}/"
        )
    
    return bucket
