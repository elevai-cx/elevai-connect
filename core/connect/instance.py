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
import pulumi_command as command

from .validation import validate_instance_alias
from .storage import associate_s3_buckets
from .logging import configure_log_retention
from .origins import create_approved_origins
from .data_streaming import create_data_streams, configure_instance_data_streaming
from .data_lake import setup_analytics_data_lake, create_lake_formation_database, create_resource_links, _get_default_data_sets
from .athena import configure_athena_workgroup, create_athena_named_queries
from ..post_deployment_tracker import add_manual_step


def create_connect_instance(
    tags: Dict[str, str],
    s3_buckets: Dict[str, aws.s3.Bucket],
    kms_key: aws.kms.Key,
    enable_data_lake: bool = True
) -> tuple[aws.connect.Instance, Dict]:
    """
    Create an Amazon Connect instance with S3 storage associations and data streaming.
    
    Args:
        tags: Tags to apply to the instance
        s3_buckets: Dictionary of S3 buckets (must include 'logging' bucket)
        kms_key: KMS key for data encryption
        enable_data_lake: Whether to enable analytics data lake (default: True)
        
    Returns:
        Tuple of (Connect instance, data streams dictionary)
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
    
    # Create Kinesis data streams BEFORE the Connect instance
    data_streams = create_data_streams(tags, kms_key)
    
    # Create CloudWatch log group if logging is enabled
    log_group = None
    if contact_flow_logs_enabled:
        log_group = configure_log_retention(instance_alias, tags)
    
    # Prepare dependencies
    depends_on_resources = []
    if data_streams.get("contact_records"):
        depends_on_resources.append(data_streams["contact_records"])
    if data_streams.get("agent_events"):
        depends_on_resources.append(data_streams["agent_events"])
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

    add_manual_step(
        title="Enable Contact Flow Features",
        doc_link="docs/POST_DEPLOYMENT_STEPS.md###1-enable-contact-flow-features",
    )
    
    # Configure data streaming for contact trace records and agent events
    configure_instance_data_streaming(connect_instance, data_streams)
    
    # Associate S3 buckets with Connect instance
    associate_s3_buckets(connect_instance, s3_buckets, kms_key)
    
    # Exports
    pulumi.export("connect_instance_id", connect_instance.id)
    pulumi.export("connect_instance_arn", connect_instance.arn)
    pulumi.export("connect_instance_status", connect_instance.status)
    pulumi.export("connect_instance_url", 
                 pulumi.Output.concat("https://", instance_alias, ".my.connect.aws"))
    
    # Export data streams if enabled
    if data_streams.get("contact_records"):
        pulumi.export("contact_records_stream_arn", data_streams["contact_records"].arn)
        pulumi.export("contact_records_stream_name", data_streams["contact_records"].name)
    if data_streams.get("agent_events"):
        pulumi.export("agent_events_stream_arn", data_streams["agent_events"].arn)
        pulumi.export("agent_events_stream_name", data_streams["agent_events"].name)
    
    # Create approved origins for CCP embedding
    approved_origins = create_approved_origins(connect_instance)
    
    # Set up analytics data lake if enabled
    if enable_data_lake:
        data_lake_setup, ram_acceptance, discover_db = setup_analytics_data_lake(
            connect_instance, tags=tags
        )
        
        # Set up Lake Formation database and resource links
        lake_config = pulumi.Config("datalake")
        if lake_config.get_bool("createLakeFormation") != False:  # Default: True
            database_name = lake_config.get("databaseName") or "connect_analytics"
            
            # Create Lake Formation database
            lf_database = create_lake_formation_database(
                database_name=database_name,
                description=f"Amazon Connect Analytics Data Lake for {instance_alias}",
                tags=tags
            )
            
            pulumi.export("lake_formation_database", lf_database.name)
            
            # Always create resource links for all shared tables
            resource_links_cmd = create_resource_links(
                database=lf_database,
                discover_command=discover_db,
                data_set_ids=None,  # None = all 27 tables
                tags=tags
            )
            
            pulumi.export("resource_links_creation_output", resource_links_cmd.stdout)
            
            # Configure Athena workgroup if bucket is available
            if "athena_queries" in s3_buckets:
                athena_workgroup = configure_athena_workgroup(
                    athena_bucket=s3_buckets["athena_queries"],
                    kms_key=kms_key,
                    workgroup_name="connect-analytics",
                    tags=tags
                )
                
                # Create helpful named queries for the resource links
                named_queries = create_athena_named_queries(
                    database_name=database_name,
                    workgroup=athena_workgroup,
                    tags=tags
                )
            else:
                pulumi.log.warn("Athena queries bucket not found - skipping Athena workgroup configuration")
    
    return connect_instance, data_streams
