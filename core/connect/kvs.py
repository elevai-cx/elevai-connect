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
Amazon Connect Kinesis Video Streams Configuration

Handles Kinesis Video Streams setup for Amazon Connect live media streaming.
Enables real-time video and audio streaming from customer interactions.
"""

from typing import Dict, Optional
import pulumi
import pulumi_aws as aws


def configure_kinesis_video_streams(
    connect_instance: aws.connect.Instance,
    tags: Dict[str, str],
    kms_key: aws.kms.Key
) -> Optional[aws.connect.InstanceStorageConfig]:
    """
    Configure Kinesis Video Streams for Amazon Connect instance.
    
    When enabled, this allows Amazon Connect to stream audio/video from
    customer interactions to Kinesis Video Streams for recording, analytics,
    and real-time processing.
    
    Common use cases:
    - Live audio streaming for sentiment analysis
    - Real-time transcription and analytics
    - Customer audio recording and archival
    - Quality monitoring and compliance
    
    Args:
        connect_instance: The Amazon Connect instance
        tags: Tags to apply to resources
        kms_key: KMS key for data encryption
        
    Returns:
        InstanceStorageConfig resource if enabled, None otherwise
    """
    config = pulumi.Config("kinesis-video-stream")
    
    # Try to get the config as an object first (for nested YAML structure)
    try:
        # For nested YAML like:
        # kinesis-video-stream:
        #   enabled: True
        #   retentionPeriodHours: 200
        kvs_config_dict = config.require_object("")
        kvs_enabled = kvs_config_dict.get("enabled", True)
        retention_period = kvs_config_dict.get("retentionPeriodHours", 24)
        prefix = kvs_config_dict.get("prefix", "elevai")
    except:
        # Fallback to reading individual keys
        # For flat structure like:
        # kinesis-video-stream:enabled: True
        # kinesis-video-stream:retentionPeriodHours: 200
        kvs_enabled = config.get_bool("enabled")
        if kvs_enabled is None:
            kvs_enabled = True
        
        retention_period = config.get_int("retentionPeriodHours")
        if retention_period is None:
            retention_period = 24
        
        prefix = config.get("prefix")
        if prefix is None:
            prefix = "elevai"
    
    pulumi.log.info(f"KVS config - enabled: {kvs_enabled}, retention: {retention_period}h, prefix: '{prefix}'")
    
    if not kvs_enabled:
        pulumi.log.info("Kinesis Video Streams disabled for Amazon Connect")
        return None
    
    kvs_config = aws.connect.InstanceStorageConfig(
        "kinesis-video-streams",
        instance_id=connect_instance.id,
        resource_type="MEDIA_STREAMS",
        storage_config=aws.connect.InstanceStorageConfigStorageConfigArgs(
            storage_type="KINESIS_VIDEO_STREAM",
            kinesis_video_stream_config=aws.connect.InstanceStorageConfigStorageConfigKinesisVideoStreamConfigArgs(
                prefix=prefix,
                retention_period_hours=retention_period,
                encryption_config=aws.connect.InstanceStorageConfigStorageConfigKinesisVideoStreamConfigEncryptionConfigArgs(
                    encryption_type="KMS",
                    key_id=kms_key.arn,
                ),
            ),
        ),
        opts=pulumi.ResourceOptions(depends_on=[connect_instance, kms_key])
    )
    
    pulumi.log.info(f"Kinesis Video Streams configured for Amazon Connect with prefix '{prefix}' and {retention_period}h retention")
    
    return kvs_config
