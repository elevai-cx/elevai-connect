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
Alerting Infrastructure

Creates SNS topics and CloudWatch alarms for monitoring Amazon Connect resources.
"""

from typing import Dict, List, Optional, Literal
from dataclasses import dataclass
import pulumi
import pulumi_aws as aws

from ..utils.naming import create_logical_name


AlertSeverity = Literal["INFO", "WARNING", "ERROR"]


@dataclass
class AlarmConfig:
    """Configuration for a CloudWatch alarm."""
    name: str
    description: str
    metric_name: str
    namespace: str
    statistic: str
    period: int
    evaluation_periods: int
    threshold: float
    comparison_operator: str
    severity: AlertSeverity
    dimensions: Optional[Dict[str, str]] = None
    treat_missing_data: str = "notBreaching"
    datapoints_to_alarm: Optional[int] = None


class AlertingInfrastructure:
    """
    Manages SNS topics and CloudWatch alarms for the Amazon Connect solution.
    
    This class provides a centralized way to create and manage alerts across
    all infrastructure resources.
    """
    
    def __init__(self, tags: Dict[str, str]):
        """
        Initialize alerting infrastructure.
        
        Args:
            tags: Common tags to apply to resources
        """
        self.tags = tags
        self.alarms: List[aws.cloudwatch.MetricAlarm] = []
        
        self.info_warning_topic = self._create_sns_topic(
            purpose="info-warning-alerts",
            display_name="Info and Warning Alerts",
            description="Notifications for informational and warning-level events"
        )
        
        self.error_topic = self._create_sns_topic(
            purpose="error-alerts",
            display_name="Error Alerts",
            description="Critical error notifications requiring immediate attention"
        )
    
    def _create_sns_topic(
        self,
        purpose: str,
        display_name: str,
        description: str
    ) -> aws.sns.Topic:
        """
        Create an SNS topic for alerts.
        
        Args:
            purpose: Descriptive purpose (e.g., 'info-warning-alerts', 'error-alerts')
            display_name: Human-readable topic name
            description: Topic description
            
        Returns:
            SNS topic resource
        """
        logical_name = create_logical_name("sns", purpose)
        
        topic = aws.sns.Topic(
            logical_name,
            display_name=display_name,
            tags={
                **self.tags,
                "Purpose": purpose,
                "Description": description
            }
        )
        
        config = pulumi.Config("alerting")
        
        if purpose == "info-warning-alerts":
            email = config.get("info_warning_email")
            if email:
                aws.sns.TopicSubscription(
                    f"{logical_name}-email-subscription",
                    topic=topic.arn,
                    protocol="email",
                    endpoint=email,
                )
        elif purpose == "error-alerts":
            email = config.get("error_email")
            if email:
                aws.sns.TopicSubscription(
                    f"{logical_name}-email-subscription",
                    topic=topic.arn,
                    protocol="email",
                    endpoint=email,
                )
        
        return topic
    
    def create_alarm(self, alarm_config: AlarmConfig) -> aws.cloudwatch.MetricAlarm:
        """
        Create a CloudWatch alarm and route it to the appropriate SNS topic.
        
        Args:
            alarm_config: Alarm configuration
            
        Returns:
            CloudWatch alarm resource
        """
        if alarm_config.severity == "ERROR":
            alarm_actions = [self.error_topic.arn]
        else:
            alarm_actions = [self.info_warning_topic.arn]
        
        logical_name = create_logical_name("alarm", alarm_config.name)
        
        alarm = aws.cloudwatch.MetricAlarm(
            logical_name,
            alarm_description=alarm_config.description,
            comparison_operator=alarm_config.comparison_operator,
            evaluation_periods=alarm_config.evaluation_periods,
            metric_name=alarm_config.metric_name,
            namespace=alarm_config.namespace,
            period=alarm_config.period,
            statistic=alarm_config.statistic,
            threshold=alarm_config.threshold,
            dimensions=alarm_config.dimensions or {},
            treat_missing_data=alarm_config.treat_missing_data,
            datapoints_to_alarm=alarm_config.datapoints_to_alarm,
            alarm_actions=alarm_actions,
            tags={
                **self.tags,
                "Severity": alarm_config.severity,
                "Purpose": alarm_config.name
            }
        )
        
        self.alarms.append(alarm)
        return alarm
    
    def get_topic_for_severity(self, severity: AlertSeverity) -> aws.sns.Topic:
        """
        Get the SNS topic for a given severity level.
        
        Args:
            severity: Alert severity (INFO, WARNING, or ERROR)
            
        Returns:
            SNS topic resource
        """
        if severity == "ERROR":
            return self.error_topic
        else:
            return self.info_warning_topic
    
    def export_outputs(self) -> Dict[str, pulumi.Output]:
        """
        Export SNS topic ARNs as Pulumi outputs.
        
        Returns:
            Dictionary of output names to values
        """
        return {
            "info_warning_topic_arn": self.info_warning_topic.arn,
            "error_topic_arn": self.error_topic.arn,
            "alarm_count": pulumi.Output.from_input(len(self.alarms))
        }


def create_alerting_infrastructure(tags: Dict[str, str]) -> AlertingInfrastructure:
    """
    Create the alerting infrastructure.
    
    Args:
        tags: Common tags to apply to resources
        
    Returns:
        AlertingInfrastructure instance
    """
    return AlertingInfrastructure(tags)
