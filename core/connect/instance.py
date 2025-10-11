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
Amazon Connect Instance - Main Orchestration

Handles the creation and configuration of Amazon Connect instances.
"""

from typing import Dict
import pulumi
import pulumi_aws as aws

from .validation import validate_instance_alias
from .storage import associate_s3_buckets, create_contact_flow_logs_firehose
from .logging import configure_log_retention
from .origins import create_approved_origins
from .data_lake import setup_analytics_data_lake


def create_connect_instance(
    tags: Dict[str, str],
    s3_buckets: Dict[str, aws.s3.Bucket],
    kms_key: aws.kms.Key,
    enable_data_lake: bool = True
) -> tuple[aws.connect.Instance, aws.kinesis.FirehoseDeliveryStream, aws.s3.Bucket]:
    """
    Create an Amazon Connect instance with S3 storage associations.
    
    Args:
        tags: Tags to apply to the instance
        s3_buckets: Dictionary of S3 buckets (must include 'logging' bucket)
        kms_key: KMS key for data encryption
        enable_data_lake: Whether to enable analytics data lake (default: True)
        
    Returns:
        Tuple of (Connect instance, Firehose stream, Firehose S3 bucket)
    """
    config = pulumi.Config("connect")
    
    # Get and validate configuration
    instance_alias = config.get("instanceAlias")
    if not instance_alias:
        raise ValueError("instanceAlias is required in Pulumi config")
    
    validate_instance_alias(instance_alias)
    
    # Get configuration with defaults
    identity_management_type = config.get("identityManagementType") or "SAML"
    inbound_calls_enabled = config.get_bool("inboundCallsEnabled")
    if inbound_calls_enabled is None:
        inbound_calls_enabled = True
    
    outbound_calls_enabled = config.get_bool("outboundCallsEnabled")
    if outbound_calls_enabled is None:
        outbound_calls_enabled = True
    
    multi_party_conference_enabled = config.get_bool("multiPartyConferenceEnabled")
    if multi_party_conference_enabled is None:
        multi_party_conference_enabled = True
    
    contact_flow_logs_enabled = config.get_bool("contactFlowLogsEnabled")
    if contact_flow_logs_enabled is None:
        contact_flow_logs_enabled = True
    
    # Validate required buckets
    if "logging" not in s3_buckets:
        raise ValueError("logging bucket must be provided in s3_buckets dictionary")
    logging_bucket = s3_buckets["logging"]
    
    # Create Firehose BEFORE the Connect instance
    firehose, firehose_bucket = create_contact_flow_logs_firehose(
        tags, kms_key, logging_bucket
    )
    
    # Create CloudWatch log group if logging is enabled
    log_group = None
    if contact_flow_logs_enabled:
        log_group = configure_log_retention(instance_alias, tags)
    
    # Prepare dependencies
    depends_on_resources = [firehose]
    if log_group:
        depends_on_resources.append(log_group)
    
    # Create the Amazon Connect instance
    connect_instance = aws.connect.Instance(
        "connect-instance",
        identity_management_type=identity_management_type,
        inbound_calls_enabled=inbound_calls_enabled,
        outbound_calls_enabled=outbound_calls_enabled,
        instance_alias=instance_alias,
        tags={**tags, "Name": f"{instance_alias}-connect-instance"},
        multi_party_conference_enabled=multi_party_conference_enabled,
        contact_flow_logs_enabled=contact_flow_logs_enabled,
        opts=pulumi.ResourceOptions(depends_on=depends_on_resources)
    )
    
    # Create storage config for contact trace records
    aws.connect.InstanceStorageConfig(
        "contact-trace-records",
        instance_id=connect_instance.id,
        resource_type="CONTACT_TRACE_RECORDS",
        storage_config=aws.connect.InstanceStorageConfigStorageConfigArgs(
            storage_type="KINESIS_FIREHOSE",
            kinesis_firehose_config=aws.connect.InstanceStorageConfigStorageConfigKinesisFirehoseConfigArgs(
                firehose_arn=firehose.arn,
            ),
        ),
        opts=pulumi.ResourceOptions(depends_on=[connect_instance, firehose])
    )
    
    # Associate S3 buckets with Connect instance
    associate_s3_buckets(connect_instance, s3_buckets, kms_key)
    
    # Exports
    pulumi.export("connect_instance_id", connect_instance.id)
    pulumi.export("connect_instance_arn", connect_instance.arn)
    pulumi.export("connect_instance_status", connect_instance.status)
    pulumi.export("connect_instance_url", 
                 pulumi.Output.concat("https://", instance_alias, ".my.connect.aws"))
    pulumi.export("firehose_arn", firehose.arn)
    
    # Create approved origins for CCP embedding
    approved_origins = create_approved_origins(connect_instance)
    
    # Set up analytics data lake if enabled
    if enable_data_lake:
        data_lake_setup, ram_acceptance = setup_analytics_data_lake(
            connect_instance, tags=tags
        )
    
    return connect_instance, firehose, firehose_bucket