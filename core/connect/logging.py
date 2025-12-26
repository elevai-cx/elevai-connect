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
Amazon Connect CloudWatch Logging Configuration

Handles CloudWatch log group setup for Connect instances.
"""

from typing import Dict
import pulumi
import pulumi_aws as aws

from ..utils.naming import create_logical_name


def configure_log_retention(
    instance_alias: str,
    tags: Dict[str, str]
) -> aws.cloudwatch.LogGroup:
    """
    Create CloudWatch log group for Amazon Connect logs.
    
    Creates the log group BEFORE the Connect instance so Amazon Connect
    can use it with the configured retention settings.
    
    Args:
        instance_alias: The instance alias for log group naming
        tags: Tags to apply to the log group
        
    Returns:
        The created CloudWatch log group
    """
    config = pulumi.Config("cloudwatch")
    log_retention_days = config.get_int("logRetentionDays") or 30
    
    log_group_name = f"/aws/connect/{instance_alias}"
    retention_in_days = None if log_retention_days == 0 else log_retention_days
    
    log_group = aws.cloudwatch.LogGroup(
        "connect-log-group",
        name=log_group_name,
        retention_in_days=retention_in_days,
        tags={**tags, "Purpose": "ConnectContactFlowLogs"}
    )
    
    # Export log configuration
    pulumi.export("connect_log_group_name", log_group.name)
    if retention_in_days:
        pulumi.export("connect_log_retention_days", retention_in_days)
    else:
        pulumi.export("connect_log_retention_days", "Never expire")
    
    return log_group
