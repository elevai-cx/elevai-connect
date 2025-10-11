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
import os
from pathlib import Path
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
    force_update = config.get_bool("forceUpdatePrimary")
    if force_update is None:
        force_update = False
    
    # Get bytes scanned cutoff (default: 10GB)
    bytes_scanned_cutoff = config.get_int("bytesScannedCutoff")
    if bytes_scanned_cutoff is None:
        bytes_scanned_cutoff = 10 * 1024 * 1024 * 1024  # 10GB
    
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
        bytes_scanned_cutoff_per_query=bytes_scanned_cutoff,
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


def _load_query_files(query_dir: str) -> Dict[str, str]:
    """
    Load all .txt query files from a directory.
    
    Args:
        query_dir: Directory path containing query files
        
    Returns:
        Dictionary mapping query names to query content
    """
    queries = {}
    query_path = Path(query_dir)
    
    if not query_path.exists():
        return queries
    
    for file_path in query_path.glob("*.txt"):
        query_name = file_path.stem  # Filename without extension
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                query_content = f.read().strip()
                queries[query_name] = query_content
        except Exception as e:
            pulumi.log.warn(f"Failed to load query file {file_path}: {e}")
    
    return queries


def create_athena_named_queries(
    database_name: str,
    workgroup: aws.athena.Workgroup,
    tags: Dict[str, str] = None
) -> Dict[str, aws.athena.NamedQuery]:
    """
    Create named queries for Connect data lake from query files.
    
    Loads queries from:
    1. ./athena-queries/ (default queries)
    2. ./custom/athena-queries/ (custom queries, if present)
    
    Args:
        database_name: Lake Formation database name
        workgroup: Athena workgroup
        tags: Tags to apply to named queries
        
    Returns:
        Dictionary of named query resources
    """
    named_queries = {}
    
    # Get the directory containing this file
    current_dir = Path(__file__).parent
    
    # Load default queries
    default_queries_dir = current_dir / "athena-queries"
    default_queries = _load_query_files(str(default_queries_dir))
    
    # Load custom queries (if they exist)
    custom_queries_dir = current_dir / "custom" / "athena-queries"
    custom_queries = _load_query_files(str(custom_queries_dir))
    
    # Merge queries (custom queries override defaults with same name)
    all_queries = {**default_queries, **custom_queries}
    
    pulumi.log.info(f"Loading {len(all_queries)} Athena queries ({len(default_queries)} default, {len(custom_queries)} custom)")
    
    # Create named queries from loaded files
    for query_name, query_template in all_queries.items():
        # Replace database name placeholder
        query_content = query_template.format(database_name=database_name)
        
        # Create a safe resource name (replace spaces and special chars with hyphens)
        resource_name = f"athena-query-{query_name.lower().replace(' ', '-').replace('_', '-')}"
        
        # Determine if this is a custom query
        is_custom = query_name in custom_queries
        description_prefix = "[Custom] " if is_custom else ""
        
        named_query = aws.athena.NamedQuery(
            resource_name,
            name=f"Connect - {query_name}",
            database=database_name,
            workgroup=workgroup.name,
            description=f"{description_prefix}{query_name}",
            query=query_content,
        )
        
        # Use sanitized name as key
        query_key = query_name.lower().replace(' ', '_').replace('-', '_')
        named_queries[query_key] = named_query
    
    pulumi.export("athena_named_queries", [q.name for q in named_queries.values()])
    
    return named_queries
