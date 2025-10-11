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
Amazon Athena Configuration for Connect Data Lake

Configures Athena workgroups for querying Connect analytics data.
"""

from typing import Dict, Optional
import pulumi
import pulumi_aws as aws


def configure_athena_workgroup(
    athena_bucket: aws.s3.Bucket,
    kms_key: aws.kms.Key,
    workgroup_name: str = "primary",
    tags: Dict[str, str] = None
) -> aws.athena.Workgroup:
    """
    Configure Athena workgroup for Connect data lake queries.
    
    Sets up the primary workgroup with S3 output location and encryption.
    
    Args:
        athena_bucket: S3 bucket for query results
        kms_key: KMS key for encryption
        workgroup_name: Name of the workgroup (default: "primary")
        tags: Tags to apply to the workgroup
        
    Returns:
        Athena workgroup resource
    """
    config = pulumi.Config("athena")
    
    # Check if we should update the primary workgroup or create a new one
    force_update = config.get_bool("forceUpdatePrimary") or False
    
    # Build output location
    output_location = pulumi.Output.concat("s3://", athena_bucket.id, "/query-results/")
    
    # Workgroup configuration
    workgroup_config = aws.athena.WorkgroupConfigurationArgs(
        enforce_workgroup_configuration=True,
        publish_cloudwatch_metrics_enabled=True,
        result_configuration=aws.athena.WorkgroupConfigurationResultConfigurationArgs(
            output_location=output_location,
            encryption_configuration=aws.athena.WorkgroupConfigurationResultConfigurationEncryptionConfigurationArgs(
                encryption_option="SSE_KMS",
                kms_key_arn=kms_key.arn,
            ),
        ),
        bytes_scanned_cutoff_per_query=config.get_int("bytesScannedCutoff") or 10 * 1024 * 1024 * 1024,  # 10GB default
    )
    
    if workgroup_name == "primary":
        # Update the primary workgroup (it already exists in AWS)
        # Note: Pulumi doesn't support updating existing resources directly,
        # so we'll create a custom workgroup instead
        workgroup_name = "connect-analytics"
        pulumi.log.info("Creating custom workgroup 'connect-analytics' (primary workgroup cannot be managed by Pulumi)")
    
    workgroup = aws.athena.Workgroup(
        f"athena-workgroup-{workgroup_name}",
        name=workgroup_name,
        description=f"Athena workgroup for Connect analytics queries",
        configuration=workgroup_config,
        force_destroy=False,
        state="ENABLED",
        tags={**tags, "Name": f"{workgroup_name}-athena-workgroup"} if tags else {"Name": f"{workgroup_name}-athena-workgroup"},
    )
    
    # Export workgroup info
    pulumi.export("athena_workgroup_name", workgroup.name)
    pulumi.export("athena_query_results_location", output_location)
    
    return workgroup


def create_athena_named_queries(
    database_name: str,
    workgroup: aws.athena.Workgroup,
    tags: Dict[str, str] = None
) -> Dict[str, aws.athena.NamedQuery]:
    """
    Create useful named queries for Connect data lake.
    
    Args:
        database_name: Lake Formation database name
        workgroup: Athena workgroup
        tags: Tags to apply to named queries
        
    Returns:
        Dictionary of named query resources
    """
    named_queries = {}
    
    # Query 1: List all resource links
    list_tables = aws.athena.NamedQuery(
        "athena-query-list-tables",
        name="Connect - List All Tables",
        database=database_name,
        workgroup=workgroup.name,
        description="List all available Connect analytics tables",
        query=f"SHOW TABLES IN {database_name}",
    )
    named_queries["list_tables"] = list_tables
    
    # Query 2: Sample contact records
    sample_contacts = aws.athena.NamedQuery(
        "athena-query-sample-contacts",
        name="Connect - Sample Contact Records",
        database=database_name,
        workgroup=workgroup.name,
        description="View sample contact records from the last 7 days",
        query=f"""
SELECT 
    contactid,
    initiationtimestamp,
    disconnecttimestamp,
    channel,
    initiationmethod
FROM {database_name}.contact_record_link
WHERE partition_0 >= date_format(current_date - interval '7' day, '%Y-%m-%d')
LIMIT 100
        """.strip(),
    )
    named_queries["sample_contacts"] = sample_contacts
    
    # Query 3: Agent performance summary
    agent_summary = aws.athena.NamedQuery(
        "athena-query-agent-summary",
        name="Connect - Agent Performance Summary",
        database=database_name,
        workgroup=workgroup.name,
        description="Daily agent performance metrics",
        query=f"""
SELECT 
    date_parse(partition_0, '%Y-%m-%d') as date,
    agentid,
    COUNT(*) as total_contacts,
    COUNT(CASE WHEN channel = 'VOICE' THEN 1 END) as voice_contacts,
    COUNT(CASE WHEN channel = 'CHAT' THEN 1 END) as chat_contacts
FROM {database_name}.contact_record_link
WHERE partition_0 >= date_format(current_date - interval '30' day, '%Y-%m-%d')
GROUP BY partition_0, agentid
ORDER BY partition_0 DESC, total_contacts DESC
        """.strip(),
    )
    named_queries["agent_summary"] = agent_summary
    
    # Query 4: Contact Lens insights
    contact_lens = aws.athena.NamedQuery(
        "athena-query-contact-lens",
        name="Connect - Contact Lens Insights",
        database=database_name,
        workgroup=workgroup.name,
        description="Contact Lens conversational analytics insights",
        query=f"""
SELECT 
    contactid,
    conversationcharacteristics.sentiment.overallsentiment.label as overall_sentiment,
    conversationcharacteristics.nontalktimepercentage,
    conversationcharacteristics.talktimepercentage
FROM {database_name}.contact_lens_conversational_analytics_link
WHERE partition_0 >= date_format(current_date - interval '7' day, '%Y-%m-%d')
LIMIT 100
        """.strip(),
    )
    named_queries["contact_lens"] = contact_lens
    
    pulumi.export("athena_named_queries", [q.name for q in named_queries.values()])
    
    return named_queries
