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
from ..utils.naming import create_logical_name


def get_retention_config(
    config: pulumi.Config,
    bucket_type: str,
    default_archive: int,
    default_deletion: int
) -> tuple[int, int]:
    """
    Get retention configuration with fallback to defaults.
    
    Args:
        config: Pulumi Config object for s3 namespace
        bucket_type: Bucket type key (e.g., 'recordings', 'chatTranscripts')
        default_archive: Default archive days
        default_deletion: Default deletion days
        
    Returns:
        Tuple of (archive_days, deletion_days)
    """
    bucket_config = config.get_object(bucket_type) or {}
    
    archive_days = bucket_config.get("archiveDays")
    if archive_days is None:
        archive_days = default_archive
    
    deletion_days = bucket_config.get("deletionDays")
    if deletion_days is None:
        deletion_days = default_deletion
    
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
    
    default_archive_days = config.get_int("archiveDays")
    if default_archive_days is None:
        default_archive_days = 90
    
    default_deletion_days = config.get_int("deletionDays")
    if default_deletion_days is None:
        default_deletion_days = 365
    
    logging_logical = create_logical_name("s3", "access-logs")
    
    logging_bucket = create_logging_bucket(
        logging_logical,
        tags,
        kms_key
    )
    
    buckets = {"logging": logging_bucket}
    
    bucket_configs = [
        ("recordings", "call-recordings", "CallRecordings"),
        ("chatTranscripts", "chat-transcripts", "ChatTranscripts"),
        ("exportedReports", "exported-reports", "ExportedReports"),
        ("attachments", "attachments", "Attachments"),
        ("screenRecordings", "screen-recordings", "ScreenRecordings"),
        ("contactEvaluations", "contact-evaluations", "ContactEvaluations"),
        ("emailMessages", "email-messages", "EmailMessages"),
        ("connectAthenaQueries", "athena-queries", "AthenaQueryResults"),
    ]
    
    for config_key, purpose, purpose_tag in bucket_configs:
        archive_days, deletion_days = get_retention_config(
            config, config_key, default_archive_days, default_deletion_days
        )
        
        logical_name = create_logical_name("s3", purpose)
        
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
            lifecycle_rules = None
        
        bucket = create_secure_s3_bucket(
            resource_name=logical_name,
            purpose=purpose_tag,
            tags=tags,
            kms_key=kms_key,
            logging_bucket=logging_bucket,
            archive_days=archive_days,
            deletion_days=deletion_days,
            lifecycle_rules=lifecycle_rules
        )
        
        bucket_key = config_key.replace("chatTranscripts", "chat_transcripts") \
                               .replace("exportedReports", "exported_reports") \
                               .replace("screenRecordings", "screen_recordings") \
                               .replace("contactEvaluations", "contact_evaluations") \
                               .replace("emailMessages", "email_messages") \
                               .replace("connectAthenaQueries", "athena_queries")
        buckets[bucket_key] = bucket
    
    return buckets
