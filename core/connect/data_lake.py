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
) -> tuple[command.local.Command, command.local.Command]:
    """
    Associate Connect analytics data lake tables and accept RAM share.
    
    Uses AWS CLI to call batch-associate-analytics-data-set API,
    then automatically accepts the RAM resource share invitation.
    
    Args:
        connect_instance: The Amazon Connect instance
        data_set_ids: List of data set IDs (None = all available)
        tags: Tags for metadata
        
    Returns:
        Tuple of (data_lake_setup command, ram_acceptance command)
    """
    if data_set_ids is None:
        data_set_ids = _get_default_data_sets()
    
    # Create data lake association
    data_lake_setup = _create_data_lake_association(
        connect_instance, data_set_ids
    )
    
    # Automatically accept RAM resource share
    ram_acceptance = _accept_ram_resource_share(
        connect_instance, data_lake_setup, tags
    )
    
    # Exports
    pulumi.export("analytics_data_lake_status", "configured")
    pulumi.export("analytics_data_lake_tables", data_set_ids)
    
    return data_lake_setup, ram_acceptance


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
            additional_secret_outputs=["stdout", "stderr"],
        ),
    )


def _accept_ram_resource_share(
    connect_instance: aws.connect.Instance,
    data_lake_setup: command.local.Command,
    tags: Dict[str, str] = None
) -> command.local.Command:
    """
    Automatically accept the RAM resource share invitation.
    
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
            additional_secret_outputs=["stdout", "stderr"],
        ),
    )
    
    pulumi.export("ram_resource_share_status", accept_share.stdout)
    
    return accept_share