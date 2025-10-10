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
Lambda Function Alarms

Defines CloudWatch alarms for Lambda functions.
"""

from typing import List
import pulumi_aws as aws

from .alerting import AlarmConfig, AlertingInfrastructure
from .config_helpers import (
    get_alarm_threshold,
    get_alarm_period,
    get_alarm_evaluation_periods
)


def create_lambda_alarms(
    functions: dict[str, aws.lambda_.Function],
    alerting: AlertingInfrastructure
) -> None:
    """
    Create CloudWatch alarms for Lambda functions.
    
    This function defines all Lambda-related alarms and creates them
    through the alerting infrastructure.
    
    Alarm thresholds can be configured in Pulumi stack config under alarms:lambda:*
    
    Args:
        functions: Dictionary of function names to Lambda resources
        alerting: Alerting infrastructure instance
    """
    
    for function_name, function in functions.items():
        # Extract the actual function name (Pulumi may add suffixes)
        function_id = function.name
        
        # Error rate alarm (ERROR severity)
        alerting.create_alarm(AlarmConfig(
            name=f"lambda-{function_name}-errors",
            description=f"Lambda function {function_name} error rate is too high",
            metric_name="Errors",
            namespace="AWS/Lambda",
            statistic="Sum",
            period=get_alarm_period("lambda", "errors", 300),
            evaluation_periods=get_alarm_evaluation_periods("lambda", "errors", 2),
            threshold=get_alarm_threshold("lambda", "errors", 5),
            comparison_operator="GreaterThanThreshold",
            severity="ERROR",
            dimensions={"FunctionName": function_id},
            treat_missing_data="notBreaching"
        ))
        
        # Throttle alarm (WARNING severity)
        alerting.create_alarm(AlarmConfig(
            name=f"lambda-{function_name}-throttles",
            description=f"Lambda function {function_name} is being throttled",
            metric_name="Throttles",
            namespace="AWS/Lambda",
            statistic="Sum",
            period=get_alarm_period("lambda", "throttles", 300),
            evaluation_periods=get_alarm_evaluation_periods("lambda", "throttles", 1),
            threshold=get_alarm_threshold("lambda", "throttles", 10),
            comparison_operator="GreaterThanThreshold",
            severity="WARNING",
            dimensions={"FunctionName": function_id},
            treat_missing_data="notBreaching"
        ))
        
        # Duration alarm (WARNING severity)
        alerting.create_alarm(AlarmConfig(
            name=f"lambda-{function_name}-duration",
            description=f"Lambda function {function_name} duration is approaching timeout",
            metric_name="Duration",
            namespace="AWS/Lambda",
            statistic="Average",
            period=get_alarm_period("lambda", "duration", 300),
            evaluation_periods=get_alarm_evaluation_periods("lambda", "duration", 2),
            threshold=get_alarm_threshold("lambda", "duration", 25000),
            comparison_operator="GreaterThanThreshold",
            severity="WARNING",
            dimensions={"FunctionName": function_id},
            treat_missing_data="notBreaching"
        ))
        
        # Concurrent executions alarm (INFO severity)
        alerting.create_alarm(AlarmConfig(
            name=f"lambda-{function_name}-concurrent-executions",
            description=f"Lambda function {function_name} concurrent executions are high",
            metric_name="ConcurrentExecutions",
            namespace="AWS/Lambda",
            statistic="Maximum",
            period=get_alarm_period("lambda", "concurrentExecutions", 60),
            evaluation_periods=get_alarm_evaluation_periods("lambda", "concurrentExecutions", 2),
            threshold=get_alarm_threshold("lambda", "concurrentExecutions", 100),
            comparison_operator="GreaterThanThreshold",
            severity="INFO",
            dimensions={"FunctionName": function_id},
            treat_missing_data="notBreaching"
        ))


def get_lambda_alarm_configs() -> List[dict]:
    """
    Get documentation for Lambda alarms.
    
    Returns a list of alarm configurations for documentation purposes.
    This helps developers understand what alarms are created.
    
    Returns:
        List of alarm configuration dictionaries
    """
    return [
        {
            "name": "Errors",
            "severity": "ERROR",
            "description": "Triggers when error count exceeds threshold",
            "config_key": "alarms:lambda:errors",
            "default_threshold": "5 errors",
            "default_period": "300 seconds (5 minutes)",
            "default_evaluation_periods": 2,
            "action": "Investigate function logs and fix errors"
        },
        {
            "name": "Throttles",
            "severity": "WARNING",
            "description": "Triggers when function is throttled",
            "config_key": "alarms:lambda:throttles",
            "default_threshold": "10 throttles",
            "default_period": "300 seconds (5 minutes)",
            "default_evaluation_periods": 1,
            "action": "Consider increasing reserved concurrency or reviewing invocation patterns"
        },
        {
            "name": "Duration",
            "severity": "WARNING",
            "description": "Triggers when duration approaches timeout",
            "config_key": "alarms:lambda:duration",
            "default_threshold": "25000 ms (25 seconds)",
            "default_period": "300 seconds (5 minutes)",
            "default_evaluation_periods": 2,
            "action": "Optimize function performance or increase timeout"
        },
        {
            "name": "Concurrent Executions",
            "severity": "INFO",
            "description": "Triggers when concurrent executions are high",
            "config_key": "alarms:lambda:concurrentExecutions",
            "default_threshold": "100 concurrent executions",
            "default_period": "60 seconds (1 minute)",
            "default_evaluation_periods": 2,
            "action": "Monitor for capacity planning"
        }
    ]
