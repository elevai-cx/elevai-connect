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
S3 Buckets for Amazon Connect

Creates Connect-specific S3 buckets using reusable utility functions.
"""

from typing import Dict
import pulumi
import pulumi_aws as aws

from core.utils import create_secure_s3_bucket, create_logging_bucket


def get_retention_config(
    config: pulumi.Config,
    bucket_type: str,
    default_archive: int,
    default_deletion: int
) -> tuple[int, int]:
    """
    Get retention configuration with fallback to defaults.
    
    Args:
        config: Pulumi config
        bucket_type: Bucket type key
        default_archive: Default archive days
        default_deletion: Default deletion days
        
    Returns:
        Tuple of (archive_days, deletion_days)
    """
    archive_days = config.get_int(f"{bucket_type}.archiveDays") or default_archive
    deletion_days = config.get_int(f"{bucket_type}.deletionDays") or default_deletion
    
    return archive_days, deletion_days


def create_s3_buckets(
    tags: Dict[str, str], 
    kms_key: aws.kms.Key
) -> Dict[str, aws.s3.Bucket]:
    """
    Create S3 buckets for Amazon Connect data storage.
    
    Uses utility functions for consistent security configuration.
    
    Args:
        tags: Tags to apply to all buckets
        kms_key: KMS key for encryption
        
    Returns:
        Dictionary of bucket names to bucket resources
    """
    config = pulumi.Config("s3")
    
    default_archive_days = config.get_int("archiveDays") or 90
    default_deletion_days = config.get_int("deletionDays") or 365
    
    # Create logging bucket first
    logging_bucket = create_logging_bucket("s3-access-logs", tags, kms_key)
    
    buckets = {"logging": logging_bucket}
    
    # Define bucket configurations
    bucket_configs = [
        ("recordings", "call-recordings", "CallRecordings"),
        ("chatTranscripts", "chat-transcripts", "ChatTranscripts"),
        ("exportedReports", "exported-reports", "ExportedReports"),
        ("attachments", "attachments", "Attachments"),
        ("screenRecordings", "screen-recordings", "ScreenRecordings"),
        ("contactEvaluations", "contact-evaluations", "ContactEvaluations"),
        ("emailMessages", "email-messages", "EmailMessages"),
        ("connectAthenaQueries", "connect-datalake-queries", "AthenaQueryResults"),
    ]
    
    # Create each bucket using utility function
    for config_key, resource_name, purpose in bucket_configs:
        archive_days, deletion_days = get_retention_config(
            config, config_key, default_archive_days, default_deletion_days
        )
        
        # Athena query results should not transition to IA (frequently accessed)
        if config_key == "connectAthenaQueries":
            lifecycle_rules = [
                aws.s3.BucketLifecycleConfigurationRuleArgs(
                    id="expire-only",
                    status="Enabled",
                    expiration=aws.s3.BucketLifecycleConfigurationRuleExpirationArgs(
                        days=deletion_days,
                    ),
                )
            ]
        else:
            lifecycle_rules = None  # Use default archive + expire
        
        bucket = create_secure_s3_bucket(
            resource_name=resource_name,
            purpose=purpose,
            tags=tags,
            kms_key=kms_key,
            logging_bucket=logging_bucket,
            archive_days=archive_days,
            deletion_days=deletion_days,
            lifecycle_rules=lifecycle_rules,
        )
        
        # Store with underscore key for backwards compatibility
        bucket_key = config_key.replace("chatTranscripts", "chat_transcripts") \
                               .replace("exportedReports", "exported_reports") \
                               .replace("screenRecordings", "screen_recordings") \
                               .replace("contactEvaluations", "contact_evaluations") \
                               .replace("emailMessages", "email_messages") \
                               .replace("connectAthenaQueries", "athena_queries")
        buckets[bucket_key] = bucket
    
    return buckets
