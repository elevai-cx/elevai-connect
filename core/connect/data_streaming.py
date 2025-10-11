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
Amazon Connect Data Streaming Configuration

Handles Kinesis stream setup for Connect instance data streaming.
Supports both contact trace records and agent event streams.
"""

from typing import Dict, Optional
import pulumi
import pulumi_aws as aws


def create_data_streams(
    tags: Dict[str, str],
    kms_key: aws.kms.Key
) -> Dict[str, Optional[aws.kinesis.Stream]]:
    """
    Create Kinesis data streams for Amazon Connect based on configuration.
    
    Supports two stream types:
    - Contact trace records
    - Agent event streams
    
    Args:
        tags: Tags to apply to resources
        kms_key: KMS key for data encryption
        
    Returns:
        Dictionary with keys 'contact_records' and 'agent_events' containing
        Stream resources or None if disabled
    """
    config = pulumi.Config("dataStreaming")
    
    streams = {}
    
    # Create contact records stream if enabled
    contact_records_config = config.get_object("contactRecords")
    if contact_records_config and contact_records_config.get("enabled"):
        streams["contact_records"] = _create_kinesis_stream(
            "contact-records",
            contact_records_config,
            tags,
            kms_key
        )
    else:
        streams["contact_records"] = None
    
    # Create agent events stream if enabled
    agent_events_config = config.get_object("agentEvents")
    if agent_events_config and agent_events_config.get("enabled"):
        streams["agent_events"] = _create_kinesis_stream(
            "agent-events",
            agent_events_config,
            tags,
            kms_key
        )
    else:
        streams["agent_events"] = None
    
    return streams


def _create_kinesis_stream(
    stream_name: str,
    config: Dict,
    tags: Dict[str, str],
    kms_key: aws.kms.Key
) -> aws.kinesis.Stream:
    """
    Create a Kinesis stream with the specified configuration.
    
    Args:
        stream_name: Name/prefix for the stream
        config: Stream configuration dictionary with keys:
                - type: "on-demand" or "provisioned"
                - shards: shard count (only for provisioned)
                - retention: retention period in days (1-7)
        tags: Tags to apply to the stream
        kms_key: KMS key for encryption
        
    Returns:
        Kinesis Stream resource
    """
    stream_type = config.get("type", "on-demand")
    retention_period = config.get("retention", 1)
    
    # Validate retention period
    if retention_period < 1 or retention_period > 7:
        raise ValueError(f"Stream retention must be between 1 and 7 days, got {retention_period}")
    
    # Build stream arguments based on type
    stream_args = {
        "name": stream_name,
        "retention_period": retention_period * 24,  # Convert days to hours
        "encryption_type": "KMS",
        "kms_key_id": kms_key.id,
        "tags": {**tags, "Name": stream_name},
    }
    
    if stream_type == "on-demand":
        stream_args["stream_mode_details"] = aws.kinesis.StreamStreamModeDetailsArgs(
            stream_mode="ON_DEMAND"
        )
    elif stream_type == "provisioned":
        shard_count = config.get("shards", 1)
        if shard_count < 1:
            raise ValueError(f"Shard count must be at least 1, got {shard_count}")
        
        stream_args["shard_count"] = shard_count
        stream_args["stream_mode_details"] = aws.kinesis.StreamStreamModeDetailsArgs(
            stream_mode="PROVISIONED"
        )
    else:
        raise ValueError(f"Invalid stream type: {stream_type}. Must be 'on-demand' or 'provisioned'")
    
    return aws.kinesis.Stream(
        stream_name,
        **stream_args,
        opts=pulumi.ResourceOptions(depends_on=[kms_key])
    )


def configure_instance_data_streaming(
    connect_instance: aws.connect.Instance,
    streams: Dict[str, Optional[aws.kinesis.Stream]]
) -> None:
    """
    Configure Amazon Connect instance to stream data to Kinesis streams.
    
    Args:
        connect_instance: The Amazon Connect instance
        streams: Dictionary with 'contact_records' and 'agent_events' streams
    """
    # Configure contact trace records streaming
    contact_records_stream = streams.get("contact_records")
    if contact_records_stream:
        aws.connect.InstanceStorageConfig(
            "contact-trace-records",
            instance_id=connect_instance.id,
            resource_type="CONTACT_TRACE_RECORDS",
            storage_config=aws.connect.InstanceStorageConfigStorageConfigArgs(
                storage_type="KINESIS_STREAM",
                kinesis_stream_config=aws.connect.InstanceStorageConfigStorageConfigKinesisStreamConfigArgs(
                    stream_arn=contact_records_stream.arn,
                ),
            ),
            opts=pulumi.ResourceOptions(depends_on=[connect_instance, contact_records_stream])
        )
    
    # Configure agent events streaming
    agent_events_stream = streams.get("agent_events")
    if agent_events_stream:
        aws.connect.InstanceStorageConfig(
            "agent-events",
            instance_id=connect_instance.id,
            resource_type="AGENT_EVENTS",
            storage_config=aws.connect.InstanceStorageConfigStorageConfigArgs(
                storage_type="KINESIS_STREAM",
                kinesis_stream_config=aws.connect.InstanceStorageConfigStorageConfigKinesisStreamConfigArgs(
                    stream_arn=agent_events_stream.arn,
                ),
            ),
            opts=pulumi.ResourceOptions(depends_on=[connect_instance, agent_events_stream])
        )
