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
SQS Queue Alarms

Defines CloudWatch alarms for SQS queues.
"""

from typing import List
import pulumi_aws as aws

from .alerting import AlarmConfig, AlertingInfrastructure
from .config_helpers import (
    get_alarm_threshold,
    get_alarm_period,
    get_alarm_evaluation_periods
)


def create_sqs_alarms(
    queues: dict[str, aws.sqs.Queue],
    alerting: AlertingInfrastructure
) -> None:
    """
    Create CloudWatch alarms for SQS queues.
    
    Only creates alarms for Dead Letter Queues (DLQs) to alert when
    messages fail processing and end up in the DLQ.
    
    Alarm thresholds can be configured in Pulumi stack config under alarms:sqs:*
    
    Args:
        queues: Dictionary of queue names to SQS queue resources
        alerting: Alerting infrastructure instance
    """
    
    for queue_name, queue in queues.items():
        # Only create alarms for DLQ queues
        if not queue_name.endswith('_dlq') and 'dlq' not in queue_name.lower():
            continue
            
        queue_id = queue.name
        
        # Messages in DLQ alarm (ERROR severity)
        # Any message in a DLQ indicates a failure that needs investigation
        alerting.create_alarm(AlarmConfig(
            name=f"sqs-{queue_name}-dlq-messages",
            description=f"SQS DLQ {queue_name} has messages indicating processing failures",
            metric_name="ApproximateNumberOfMessagesVisible",
            namespace="AWS/SQS",
            statistic="Sum",
            period=get_alarm_period("sqs", "dlqMessages", 300),
            evaluation_periods=get_alarm_evaluation_periods("sqs", "dlqMessages", 1),
            threshold=get_alarm_threshold("sqs", "dlqMessages", 1),
            comparison_operator="GreaterThanOrEqualToThreshold",
            severity="ERROR",
            dimensions={"QueueName": queue_id},
            treat_missing_data="notBreaching"
        ))
        
        # DLQ age alarm (WARNING severity)
        # Messages sitting in DLQ for a long time
        alerting.create_alarm(AlarmConfig(
            name=f"sqs-{queue_name}-dlq-message-age",
            description=f"SQS DLQ {queue_name} has old messages that need attention",
            metric_name="ApproximateAgeOfOldestMessage",
            namespace="AWS/SQS",
            statistic="Maximum",
            period=get_alarm_period("sqs", "dlqMessageAge", 300),
            evaluation_periods=get_alarm_evaluation_periods("sqs", "dlqMessageAge", 2),
            threshold=get_alarm_threshold("sqs", "dlqMessageAge", 3600),
            comparison_operator="GreaterThanThreshold",
            severity="WARNING",
            dimensions={"QueueName": queue_id},
            treat_missing_data="notBreaching"
        ))


def get_sqs_alarm_configs() -> List[dict]:
    """
    Get documentation for SQS alarms.
    
    Returns:
        List of alarm configuration dictionaries
    """
    return [
        {
            "name": "DLQ Messages",
            "severity": "ERROR",
            "description": "Triggers when any messages appear in the DLQ",
            "config_key": "alarms:sqs:dlqMessages",
            "default_threshold": "1 message",
            "default_period": "300 seconds (5 minutes)",
            "default_evaluation_periods": 1,
            "action": "Investigate failed messages and fix processing issues"
        },
        {
            "name": "DLQ Message Age",
            "severity": "WARNING",
            "description": "Triggers when messages sit in DLQ for too long",
            "config_key": "alarms:sqs:dlqMessageAge",
            "default_threshold": "3600 seconds (1 hour)",
            "default_period": "300 seconds (5 minutes)",
            "default_evaluation_periods": 2,
            "action": "Review and process or purge old DLQ messages"
        }
    ]
