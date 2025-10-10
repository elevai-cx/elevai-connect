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
Amazon Connect Instance Alarms

Defines CloudWatch alarms for Amazon Connect instances.
"""

from typing import List
import pulumi_aws as aws

from .alerting import AlarmConfig, AlertingInfrastructure
from .config_helpers import (
    get_alarm_config,
    get_alarm_threshold,
    get_alarm_period,
    get_alarm_evaluation_periods
)


def create_connect_alarms(
    connect_instance: aws.connect.Instance,
    alerting: AlertingInfrastructure
) -> None:
    """
    Create CloudWatch alarms for Amazon Connect instance.
    
    Alarm thresholds can be configured in Pulumi stack config under alarms:connect:*
    
    Args:
        connect_instance: Amazon Connect instance
        alerting: Alerting infrastructure instance
    """
    
    instance_id = connect_instance.id
    
    # Get concurrent percentage thresholds
    warning_threshold = get_alarm_config("connect", "concurrentPercentageWarning", "", 80)
    critical_threshold = get_alarm_config("connect", "concurrentPercentageCritical", "", 95)
    concurrent_period = get_alarm_config("connect", "concurrentPeriod", "", 60)
    warning_eval_periods = get_alarm_config("connect", "concurrentEvaluationPeriodsWarning", "", 3)
    critical_eval_periods = get_alarm_config("connect", "concurrentEvaluationPeriodsCritical", "", 2)
    
    # Voice Calls - Concurrent calls percentage alarm (WARNING severity)
    alerting.create_alarm(AlarmConfig(
        name="connect-concurrent-calls-percentage-high",
        description="Amazon Connect concurrent calls percentage is approaching limit",
        metric_name="ConcurrentCallsPercentage",
        namespace="AWS/Connect",
        statistic="Maximum",
        period=concurrent_period,
        evaluation_periods=warning_eval_periods,
        threshold=warning_threshold,
        comparison_operator="GreaterThanThreshold",
        severity="WARNING",
        dimensions={"InstanceId": instance_id, "MetricGroup": "VoiceCalls"},
        treat_missing_data="notBreaching"
    ))
    
    # Voice Calls - Concurrent calls percentage critical (ERROR severity)
    alerting.create_alarm(AlarmConfig(
        name="connect-concurrent-calls-percentage-critical",
        description="Amazon Connect concurrent calls percentage is critically high",
        metric_name="ConcurrentCallsPercentage",
        namespace="AWS/Connect",
        statistic="Maximum",
        period=concurrent_period,
        evaluation_periods=critical_eval_periods,
        threshold=critical_threshold,
        comparison_operator="GreaterThanThreshold",
        severity="ERROR",
        dimensions={"InstanceId": instance_id, "MetricGroup": "VoiceCalls"},
        treat_missing_data="notBreaching"
    ))
    
    # Chats - Concurrent chats percentage alarm (WARNING severity)
    alerting.create_alarm(AlarmConfig(
        name="connect-concurrent-chats-percentage-high",
        description="Amazon Connect concurrent chats percentage is approaching limit",
        metric_name="ConcurrentChatsPercentage",
        namespace="AWS/Connect",
        statistic="Maximum",
        period=concurrent_period,
        evaluation_periods=warning_eval_periods,
        threshold=warning_threshold,
        comparison_operator="GreaterThanThreshold",
        severity="WARNING",
        dimensions={"InstanceId": instance_id, "MetricGroup": "Chat"},
        treat_missing_data="notBreaching"
    ))
    
    # Chats - Concurrent chats percentage critical (ERROR severity)
    alerting.create_alarm(AlarmConfig(
        name="connect-concurrent-chats-percentage-critical",
        description="Amazon Connect concurrent chats percentage is critically high",
        metric_name="ConcurrentChatsPercentage",
        namespace="AWS/Connect",
        statistic="Maximum",
        period=concurrent_period,
        evaluation_periods=critical_eval_periods,
        threshold=critical_threshold,
        comparison_operator="GreaterThanThreshold",
        severity="ERROR",
        dimensions={"InstanceId": instance_id, "MetricGroup": "Chat"},
        treat_missing_data="notBreaching"
    ))
    
    # Email - Concurrent emails percentage alarm (WARNING severity)
    alerting.create_alarm(AlarmConfig(
        name="connect-concurrent-emails-percentage-high",
        description="Amazon Connect concurrent emails percentage is approaching limit",
        metric_name="ConcurrentEmailsPercentage",
        namespace="AWS/Connect",
        statistic="Maximum",
        period=concurrent_period,
        evaluation_periods=warning_eval_periods,
        threshold=warning_threshold,
        comparison_operator="GreaterThanThreshold",
        severity="WARNING",
        dimensions={"InstanceId": instance_id, "MetricGroup": "Email"},
        treat_missing_data="notBreaching"
    ))
    
    # Email - Concurrent emails percentage critical (ERROR severity)
    alerting.create_alarm(AlarmConfig(
        name="connect-concurrent-emails-percentage-critical",
        description="Amazon Connect concurrent emails percentage is critically high",
        metric_name="ConcurrentEmailsPercentage",
        namespace="AWS/Connect",
        statistic="Maximum",
        period=concurrent_period,
        evaluation_periods=critical_eval_periods,
        threshold=critical_threshold,
        comparison_operator="GreaterThanThreshold",
        severity="ERROR",
        dimensions={"InstanceId": instance_id, "MetricGroup": "Email"},
        treat_missing_data="notBreaching"
    ))
    
    # Tasks - Concurrent tasks percentage alarm (WARNING severity)
    alerting.create_alarm(AlarmConfig(
        name="connect-concurrent-tasks-percentage-high",
        description="Amazon Connect concurrent tasks percentage is approaching limit",
        metric_name="ConcurrentTasksPercentage",
        namespace="AWS/Connect",
        statistic="Maximum",
        period=concurrent_period,
        evaluation_periods=warning_eval_periods,
        threshold=warning_threshold,
        comparison_operator="GreaterThanThreshold",
        severity="WARNING",
        dimensions={"InstanceId": instance_id, "MetricGroup": "Tasks"},
        treat_missing_data="notBreaching"
    ))
    
    # Tasks - Concurrent tasks percentage critical (ERROR severity)
    alerting.create_alarm(AlarmConfig(
        name="connect-concurrent-tasks-percentage-critical",
        description="Amazon Connect concurrent tasks percentage is critically high",
        metric_name="ConcurrentTasksPercentage",
        namespace="AWS/Connect",
        statistic="Maximum",
        period=concurrent_period,
        evaluation_periods=critical_eval_periods,
        threshold=critical_threshold,
        comparison_operator="GreaterThanThreshold",
        severity="ERROR",
        dimensions={"InstanceId": instance_id, "MetricGroup": "Tasks"},
        treat_missing_data="notBreaching"
    ))
    
    # Missed calls alarm (WARNING severity)
    alerting.create_alarm(AlarmConfig(
        name="connect-missed-calls",
        description="Amazon Connect is experiencing missed calls",
        metric_name="MissedCalls",
        namespace="AWS/Connect",
        statistic="Sum",
        period=get_alarm_period("connect", "missedCalls", 300),
        evaluation_periods=get_alarm_evaluation_periods("connect", "missedCalls", 1),
        threshold=get_alarm_threshold("connect", "missedCalls", 5),
        comparison_operator="GreaterThanThreshold",
        severity="WARNING",
        dimensions={"InstanceId": instance_id, "MetricGroup": "VoiceCalls"},
        treat_missing_data="notBreaching"
    ))
    
    # Throttled calls alarm (ERROR severity)
    alerting.create_alarm(AlarmConfig(
        name="connect-throttled-calls",
        description="Amazon Connect calls are being throttled",
        metric_name="ThrottledCalls",
        namespace="AWS/Connect",
        statistic="Sum",
        period=get_alarm_period("connect", "throttledCalls", 300),
        evaluation_periods=get_alarm_evaluation_periods("connect", "throttledCalls", 1),
        threshold=get_alarm_threshold("connect", "throttledCalls", 1),
        comparison_operator="GreaterThanThreshold",
        severity="ERROR",
        dimensions={"InstanceId": instance_id, "MetricGroup": "VoiceCalls"},
        treat_missing_data="notBreaching"
    ))
    
    # Contact flow errors alarm (ERROR severity)
    alerting.create_alarm(AlarmConfig(
        name="connect-contact-flow-errors",
        description="Amazon Connect contact flows are experiencing errors",
        metric_name="ContactFlowErrors",
        namespace="AWS/Connect",
        statistic="Sum",
        period=get_alarm_period("connect", "contactFlowErrors", 300),
        evaluation_periods=get_alarm_evaluation_periods("connect", "contactFlowErrors", 2),
        threshold=get_alarm_threshold("connect", "contactFlowErrors", 5),
        comparison_operator="GreaterThanThreshold",
        severity="ERROR",
        dimensions={"InstanceId": instance_id, "MetricGroup": "ContactFlow"},
        treat_missing_data="notBreaching"
    ))
    
    # Call recording upload errors alarm (ERROR severity)
    alerting.create_alarm(AlarmConfig(
        name="connect-call-recording-upload-error",
        description="Amazon Connect call recordings failed to upload to S3",
        metric_name="CallRecordingUploadError",
        namespace="AWS/Connect",
        statistic="Sum",
        period=get_alarm_period("connect", "callRecordingUploadError", 300),
        evaluation_periods=get_alarm_evaluation_periods("connect", "callRecordingUploadError", 1),
        threshold=get_alarm_threshold("connect", "callRecordingUploadError", 1),
        comparison_operator="GreaterThanThreshold",
        severity="ERROR",
        dimensions={"InstanceId": instance_id, "MetricGroup": "CallRecordings"},
        treat_missing_data="notBreaching"
    ))
    
    # Contact flow fatal errors alarm (ERROR severity)
    alerting.create_alarm(AlarmConfig(
        name="connect-contact-flow-fatal-errors",
        description="Amazon Connect contact flows are experiencing fatal system errors",
        metric_name="ContactFlowFatalErrors",
        namespace="AWS/Connect",
        statistic="Sum",
        period=get_alarm_period("connect", "contactFlowFatalErrors", 300),
        evaluation_periods=get_alarm_evaluation_periods("connect", "contactFlowFatalErrors", 1),
        threshold=get_alarm_threshold("connect", "contactFlowFatalErrors", 1),
        comparison_operator="GreaterThanThreshold",
        severity="ERROR",
        dimensions={"InstanceId": instance_id, "MetricGroup": "ContactFlow"},
        treat_missing_data="notBreaching"
    ))
    
    # Misconfigured phone numbers alarm (ERROR severity)
    alerting.create_alarm(AlarmConfig(
        name="connect-misconfigured-phone-numbers",
        description="Amazon Connect calls are failing due to misconfigured phone numbers",
        metric_name="MisconfiguredPhoneNumbers",
        namespace="AWS/Connect",
        statistic="Sum",
        period=get_alarm_period("connect", "misconfiguredPhoneNumbers", 300),
        evaluation_periods=get_alarm_evaluation_periods("connect", "misconfiguredPhoneNumbers", 1),
        threshold=get_alarm_threshold("connect", "misconfiguredPhoneNumbers", 1),
        comparison_operator="GreaterThanThreshold",
        severity="ERROR",
        dimensions={"InstanceId": instance_id, "MetricGroup": "VoiceCalls"},
        treat_missing_data="notBreaching"
    ))
    
    # Queue capacity exceeded alarm (WARNING severity)
    alerting.create_alarm(AlarmConfig(
        name="connect-queue-capacity-exceeded",
        description="Amazon Connect calls are being rejected because queues are full",
        metric_name="QueueCapacityExceededError",
        namespace="AWS/Connect",
        statistic="Sum",
        period=get_alarm_period("connect", "queueCapacityExceededError", 300),
        evaluation_periods=get_alarm_evaluation_periods("connect", "queueCapacityExceededError", 2),
        threshold=get_alarm_threshold("connect", "queueCapacityExceededError", 5),
        comparison_operator="GreaterThanThreshold",
        severity="WARNING",
        dimensions={"InstanceId": instance_id, "MetricGroup": "Queue"},
        treat_missing_data="notBreaching"
    ))
    
    # Packet loss rate alarm (WARNING severity)
    alerting.create_alarm(AlarmConfig(
        name="connect-packet-loss-rate",
        description="Amazon Connect is experiencing high packet loss on calls",
        metric_name="ToInstancePacketLossRate",
        namespace="AWS/Connect",
        statistic="Average",
        period=get_alarm_period("connect", "toInstancePacketLossRate", 60),
        evaluation_periods=get_alarm_evaluation_periods("connect", "toInstancePacketLossRate", 3),
        threshold=get_alarm_threshold("connect", "toInstancePacketLossRate", 5),
        comparison_operator="GreaterThanThreshold",
        severity="WARNING",
        dimensions={
            "InstanceId": instance_id,
            "Participant": "Agent",
            "Type of Connection": "WebRTC",
            "Stream Type": "Voice"
        },
        treat_missing_data="notBreaching"
    ))


def get_connect_alarm_configs() -> List[dict]:
    """
    Get documentation for Amazon Connect alarms.
    
    Returns:
        List of alarm configuration dictionaries
    """
    return [
        {
            "name": "Concurrent Calls/Chats/Emails/Tasks Percentage High",
            "severity": "WARNING",
            "description": "Triggers when concurrent activity reaches warning threshold",
            "config_key": "alarms:connect:concurrentPercentageWarning",
            "default_threshold": "80%",
            "default_period": "60 seconds (1 minute)",
            "default_evaluation_periods": 3,
            "action": "Monitor capacity and prepare for scaling if needed"
        },
        {
            "name": "Concurrent Calls/Chats/Emails/Tasks Percentage Critical",
            "severity": "ERROR",
            "description": "Triggers when concurrent activity reaches critical threshold",
            "config_key": "alarms:connect:concurrentPercentageCritical",
            "default_threshold": "95%",
            "default_period": "60 seconds (1 minute)",
            "default_evaluation_periods": 2,
            "action": "Request service limit increase immediately"
        },
        {
            "name": "Missed Calls",
            "severity": "WARNING",
            "description": "Triggers when calls are missed",
            "config_key": "alarms:connect:missedCalls",
            "default_threshold": "5 missed calls",
            "default_period": "300 seconds (5 minutes)",
            "default_evaluation_periods": 1,
            "action": "Check agent availability and routing configuration"
        },
        {
            "name": "Throttled Calls",
            "severity": "ERROR",
            "description": "Triggers when API calls are throttled",
            "config_key": "alarms:connect:throttledCalls",
            "default_threshold": "1 throttled call",
            "default_period": "300 seconds (5 minutes)",
            "default_evaluation_periods": 1,
            "action": "Review API usage patterns and request limit increase"
        },
        {
            "name": "Contact Flow Errors",
            "severity": "ERROR",
            "description": "Triggers when contact flows error",
            "config_key": "alarms:connect:contactFlowErrors",
            "default_threshold": "5 errors",
            "default_period": "300 seconds (5 minutes)",
            "default_evaluation_periods": 2,
            "action": "Review contact flow logs and fix configuration issues"
        },
        {
            "name": "Call Recording Upload Errors",
            "severity": "ERROR",
            "description": "Triggers when call recordings fail to upload to S3",
            "config_key": "alarms:connect:callRecordingUploadError",
            "default_threshold": "1 error",
            "default_period": "300 seconds (5 minutes)",
            "default_evaluation_periods": 1,
            "action": "Check S3 bucket permissions and configuration"
        },
        {
            "name": "Contact Flow Fatal Errors",
            "severity": "ERROR",
            "description": "Triggers when contact flows experience fatal system errors",
            "config_key": "alarms:connect:contactFlowFatalErrors",
            "default_threshold": "1 error",
            "default_period": "300 seconds (5 minutes)",
            "default_evaluation_periods": 1,
            "action": "Review contact flow configuration and AWS service health"
        },
        {
            "name": "Misconfigured Phone Numbers",
            "severity": "ERROR",
            "description": "Triggers when calls fail due to phone number misconfiguration",
            "config_key": "alarms:connect:misconfiguredPhoneNumbers",
            "default_threshold": "1 error",
            "default_period": "300 seconds (5 minutes)",
            "default_evaluation_periods": 1,
            "action": "Check phone number to contact flow associations"
        },
        {
            "name": "Queue Capacity Exceeded",
            "severity": "WARNING",
            "description": "Triggers when calls are rejected because queues are full",
            "config_key": "alarms:connect:queueCapacityExceededError",
            "default_threshold": "5 errors",
            "default_period": "300 seconds (5 minutes)",
            "default_evaluation_periods": 2,
            "action": "Increase queue capacity or add more agents"
        },
        {
            "name": "Packet Loss Rate",
            "severity": "WARNING",
            "description": "Triggers when call quality degrades due to packet loss",
            "config_key": "alarms:connect:toInstancePacketLossRate",
            "default_threshold": "5% packet loss",
            "default_period": "60 seconds (1 minute)",
            "default_evaluation_periods": 3,
            "action": "Check network connectivity and agent internet connections"
        }
    ]
