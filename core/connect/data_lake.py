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
Amazon Connect Analytics Data Lake

Handles data lake setup and RAM resource share acceptance.
"""

from typing import Optional, List, Dict
import json
import pulumi
import pulumi_aws as aws
import pulumi_command as command


def setup_analytics_data_lake(
    connect_instance: aws.connect.Instance,
    data_set_ids: Optional[List[str]] = None,
    tags: Dict[str, str] = None
) -> tuple[command.local.Command, command.local.Command, command.local.Command]:
    """
    Associate Connect analytics data lake tables and accept RAM share.
    
    Uses AWS CLI to call batch-associate-analytics-data-set API,
    then automatically accepts the RAM resource share invitation,
    and discovers the shared database information.
    
    Args:
        connect_instance: The Amazon Connect instance
        data_set_ids: List of data set IDs (None = all available)
        tags: Tags for metadata
        
    Returns:
        Tuple of (data_lake_setup command, ram_acceptance command, discover_command)
    """
    if data_set_ids is None:
        data_set_ids = _get_default_data_sets()
    
    # Create data lake association
    data_lake_setup = _create_data_lake_association(
        connect_instance, data_set_ids
    )
    
    # Automatically accept RAM resource share and discover shared database
    ram_acceptance, discover_db = _accept_ram_resource_share(
        connect_instance, data_lake_setup, tags
    )
    
    return data_lake_setup, ram_acceptance, discover_db


def _get_default_data_sets() -> List[str]:
    """Get the full list of available data lake tables."""
    return [
        "contact_record",
        "contact_lens_conversational_analytics",
        "contact_statistic_record",
        "agent_queue_statistic_record",
        "agent_statistic_record",
        "contact_evaluation_record",
        "contact_flow_events",
        "bot_conversations",
        "bot_intents",
        "bot_slots",
        "routing_profiles",
        "users",
        "agent_hierarchy_groups",
        "staff_shifts",
        "shift_activities",
        "staff_timeoff_intervals",
        "staffing_group_forecast_groups",
        "staff_timeoff_balance_changes",
        "forecast_groups",
        "long_term_forecasts",
        "staff_shift_activities",
        "shift_profiles",
        "staffing_group_supervisors",
        "short_term_forecasts",
        "staffing_groups",
        "staff_timeoffs",
        "staff_scheduling_profile"
    ]


def _create_data_lake_association(
    connect_instance: aws.connect.Instance,
    data_set_ids: List[str]
) -> command.local.Command:
    """Create the data lake association using AWS CLI."""
    current = aws.get_caller_identity()
    account_id = current.account_id
    
    input_data = pulumi.Output.all(
        instance_id=connect_instance.id,
        account_id=account_id
    ).apply(lambda args: json.dumps({
        "InstanceId": args["instance_id"],
        "DataSetIds": data_set_ids,
        "TargetAccountId": args["account_id"],
    }, indent=2))
    
    cli_command = input_data.apply(
        lambda json_input: (
            f"TMPFILE=$(mktemp) && "
            f"cat > $TMPFILE << 'EOF'\n{json_input}\nEOF\n"
            f"aws connect batch-associate-analytics-data-set "
            f"--cli-input-json file://$TMPFILE && "
            f"rm -f $TMPFILE"
        )
    )
    
    return command.local.Command(
        "analytics-data-lake-setup",
        create=cli_command,
        opts=pulumi.ResourceOptions(
            depends_on=[connect_instance],
        ),
    )


def _accept_ram_resource_share(
    connect_instance: aws.connect.Instance,
    data_lake_setup: command.local.Command,
    tags: Dict[str, str] = None
) -> tuple[command.local.Command, command.local.Command]:
    """
    Automatically accept the RAM resource share invitation and discover shared database info.
    
    Returns a tuple of (accept_command, discover_command) where discover_command outputs
    the shared database name and source account ID.
    
    Runs AFTER data_lake_setup completes to find and accept
    the pending LakeFormation resource share invitation.
    """
    current = aws.get_caller_identity()
    account_id = current.account_id
    
    accept_command = pulumi.Output.all(
        account_id=account_id
    ).apply(lambda args: (
        "INVITATION_ARN=$(aws ram get-resource-share-invitations "
        "--query 'resourceShareInvitations[?contains(resourceShareName, `LakeFormation`) && status==`PENDING`].resourceShareInvitationArn' "
        "--output text | head -1) && "
        "if [ -n \"$INVITATION_ARN\" ] && [ \"$INVITATION_ARN\" != \"None\" ]; then "
        "  aws ram accept-resource-share-invitation --resource-share-invitation-arn $INVITATION_ARN; "
        "else "
        "  echo 'No pending LakeFormation resource share invitation found'; "
        "fi"
    ))
    
    accept_share = command.local.Command(
        "accept-ram-resource-share",
        create=accept_command,
        opts=pulumi.ResourceOptions(
            depends_on=[data_lake_setup, connect_instance],
        ),
    )
    
    # Discover the shared database info from RAM
    discover_command = command.local.Command(
        "discover-shared-database",
        create=pulumi.Output.all(connect_instance.id).apply(lambda args: f"""#!/bin/bash
set -e

# Get the first shared Glue database from RAM
SHARED_DB=$(aws ram list-resources \
  --resource-owner OTHER-ACCOUNTS \
  --resource-type glue:Database \
  --query 'resources[0].arn' \
  --output text 2>/dev/null | head -1 | tr -d '\n')

if [ "$SHARED_DB" = "None" ] || [ -z "$SHARED_DB" ]; then
  # Fallback: use connect_{{instance_id}} format
  printf '{{"database_name":"connect_{args[0]}","account_id":""}}'
  exit 0
fi

# Extract database name and account ID from ARN
# ARN format: arn:aws:glue:region:account-id:database/database-name
ACCOUNT_ID=$(echo "$SHARED_DB" | cut -d':' -f5)
DB_NAME=$(echo "$SHARED_DB" | cut -d'/' -f2 | tr -d '\n')

printf '{{"database_name":"%s","account_id":"%s"}}' "$DB_NAME" "$ACCOUNT_ID"
"""),
        opts=pulumi.ResourceOptions(
            depends_on=[accept_share],
        ),
    )
    
    pulumi.export("ram_resource_share_status", accept_share.stdout)
    pulumi.export("shared_database_info", discover_command.stdout)
    
    return accept_share, discover_command


def create_lake_formation_database(
    database_name: str,
    description: str = "Amazon Connect Analytics Data Lake Database",
    location_uri: Optional[str] = None,
    tags: Dict[str, str] = None
) -> aws.glue.CatalogDatabase:
    """
    Create a Lake Formation database for Amazon Connect analytics tables.
    
    Args:
        database_name: Name of the Lake Formation database
        description: Database description
        location_uri: Optional S3 location URI for the database
        tags: Tags to apply to the database
        
    Returns:
        The Lake Formation database resource
    """
    catalog_id = aws.get_caller_identity().account_id
    
    database = aws.glue.CatalogDatabase(
        f"connect-analytics-{database_name}",
        name=database_name,
        description=description,
        location_uri=location_uri,
        catalog_id=catalog_id,
    )
    
    # Grant Lake Formation permissions to the database
    # This ensures the current principal has admin access
    current_caller = aws.get_caller_identity()
    current_arn = current_caller.arn
    
    pulumi.export(f"lakeformation_database_name", database.name)
    pulumi.export(f"lakeformation_database_catalog_id", database.catalog_id)
    
    return database


def create_resource_links(
    database: aws.glue.CatalogDatabase,
    discover_command: command.local.Command,
    data_set_ids: Optional[List[str]] = None,
    tags: Dict[str, str] = None
) -> command.local.Command:
    """
    Create Lake Formation resource links for shared Amazon Connect tables using AWS CLI.
    
    This creates resource links (table links) in the consumer account that point
    to the shared tables from the producer account. Uses the discovered shared database
    information from RAM.
    
    Args:
        database: The Lake Formation database to create resource links in
        discover_command: Command that discovered shared database info (provides JSON with database_name and account_id)
        data_set_ids: List of data set IDs to create links for (None = all available)
        tags: Tags to apply to resource links
        
    Returns:
        Command resource that creates all resource links
    """
    # Get default data sets if none specified
    if data_set_ids is None:
        data_set_ids = _get_default_data_sets()
    
    current_account = aws.get_caller_identity()
    catalog_id = current_account.account_id
    
    # Build the CLI command that creates all resource links
    create_command = pulumi.Output.all(
        database_name=database.name,
        catalog_id=catalog_id,
        shared_db_info=discover_command.stdout,
    ).apply(lambda args: f'''#!/bin/bash
set -e

# Verify required tools are installed
if ! command -v jq &> /dev/null; then
  echo "Error: jq is required but not installed"
  echo "Install with: brew install jq (macOS) or apt-get install jq (Ubuntu)"
  exit 1
fi

if ! command -v aws &> /dev/null; then
  echo "Error: AWS CLI is required but not installed"
  echo "Install from: https://aws.amazon.com/cli/"
  exit 1
fi

# Read shared database info from stdin and parse with jq
read -r SHARED_INFO << 'EOF'
{args["shared_db_info"].strip()}
EOF

SOURCE_DB=$(echo "$SHARED_INFO" | jq -r '.database_name')
SOURCE_ACCOUNT=$(echo "$SHARED_INFO" | jq -r '.account_id')
TARGET_DB="{args["database_name"]}"
TARGET_CATALOG="{args["catalog_id"]}"

echo "Creating resource links in $TARGET_DB from $SOURCE_DB (account: $SOURCE_ACCOUNT)"

# List of tables to create links for
TABLES=({" ".join(data_set_ids)})

# Counter for created links
CREATED=0
SKIPPED=0

for TABLE in "${{TABLES[@]}}"; do
  LINK_NAME="${{TABLE}}_link"
  
  # Check if resource link already exists
  if aws glue get-table \
    --database-name "$TARGET_DB" \
    --name "$LINK_NAME" \
    --catalog-id "$TARGET_CATALOG" \
    >/dev/null 2>&1; then
    echo "Resource link $LINK_NAME already exists, skipping"
    SKIPPED=$((SKIPPED + 1))
    continue
  fi
  
  # Create resource link using temp file for JSON
  echo "Creating resource link: $LINK_NAME -> $TABLE"
  TMPFILE=$(mktemp)
  cat > $TMPFILE << JSONEOF
{{
  "Name": "$LINK_NAME",
  "TableType": "VIRTUAL_VIEW",
  "TargetTable": {{
    "CatalogId": "$SOURCE_ACCOUNT",
    "DatabaseName": "$SOURCE_DB",
    "Name": "$TABLE"
  }}
}}
JSONEOF
  
  aws glue create-table \
    --database-name "$TARGET_DB" \
    --catalog-id "$TARGET_CATALOG" \
    --table-input file://$TMPFILE
  
  rm -f $TMPFILE
  CREATED=$((CREATED + 1))
done

echo "Resource links created: $CREATED, skipped: $SKIPPED, total: $((CREATED + SKIPPED))"
printf '{{"created":%d,"skipped":%d,"total":%d}}' $CREATED $SKIPPED $((CREATED + SKIPPED))
''')
    
    resource_links_cmd = command.local.Command(
        "create-resource-links",
        create=create_command,
        opts=pulumi.ResourceOptions(
            depends_on=[database, discover_command],
        ),
    )
    
    pulumi.export("resource_links_result", resource_links_cmd.stdout)
    
    return resource_links_cmd


def setup_complete_analytics_data_lake(
    connect_instance: aws.connect.Instance,
    database_name: str,
    data_set_ids: Optional[List[str]] = None,
    tags: Dict[str, str] = None
) -> dict:
    """
    Complete end-to-end setup of Amazon Connect Analytics Data Lake.
    
    This orchestrates:
    1. Data lake association with Connect
    2. RAM resource share acceptance
    3. Shared database discovery from RAM
    4. Lake Formation database creation
    5. Resource link creation for all shared tables
    
    Args:
        connect_instance: The Amazon Connect instance
        database_name: Name for the Lake Formation database
        data_set_ids: List of data set IDs (None = all available)
        tags: Tags for all resources
        
    Returns:
        Dictionary containing all created resources
    """
    if data_set_ids is None:
        data_set_ids = _get_default_data_sets()
    
    # Step 1, 2 & 3: Associate data lake, accept RAM share, and discover shared database
    data_lake_setup, ram_acceptance, discover_db = setup_analytics_data_lake(
        connect_instance, data_set_ids, tags
    )
    
    # Step 4: Create Lake Formation database
    database = create_lake_formation_database(
        database_name=database_name,
        tags=tags
    )
    
    # Step 5: Create resource links for all shared tables using CLI
    resource_links_cmd = create_resource_links(
        database=database,
        discover_command=discover_db,
        data_set_ids=data_set_ids,
        tags=tags
    )
    
    pulumi.export("analytics_setup_complete", True)
    pulumi.export("expected_resource_link_count", len(data_set_ids))
    
    return {
        "data_lake_setup": data_lake_setup,
        "ram_acceptance": ram_acceptance,
        "discover_db": discover_db,
        "database": database,
        "resource_links": resource_links_cmd,
    }


def create_athena_verification_query(
    database: aws.glue.CatalogDatabase,
    resource_links_cmd: command.local.Command,
    table_name: str = "contact_record_link",
    workgroup: str = "primary",
    output_location: Optional[str] = None,
) -> command.local.Command:
    """
    Create an Athena query to verify data lake access.
    
    This creates a verification query that checks if data is accessible
    through the resource links.
    
    Args:
        database: The Lake Formation database
        resource_links_cmd: The command that created resource links (for dependency)
        table_name: Name of the resource link table to query (default: contact_record_link)
        workgroup: Athena workgroup to use (default: "primary")
        output_location: S3 location for query results (optional)
        
    Returns:
        Command resource that runs the verification query
    """
    # Build the query command
    query_cmd = pulumi.Output.all(
        database_name=database.name,
        workgroup=workgroup
    ).apply(lambda args: (
        f"aws athena start-query-execution "
        f"--query-string 'SELECT * FROM {args['database_name']}.{table_name} LIMIT 10' "
        f"--work-group {args['workgroup']} "
        + (f"--result-configuration 'OutputLocation={output_location}' " if output_location else "")
        + "--query 'QueryExecutionId' --output text"
    ))
    
    verification_query = command.local.Command(
        "athena-verification-query",
        create=query_cmd,
        opts=pulumi.ResourceOptions(
            depends_on=[resource_links_cmd],
        ),
    )
    
    pulumi.export("athena_verification_query_id", verification_query.stdout)
    
    return verification_query