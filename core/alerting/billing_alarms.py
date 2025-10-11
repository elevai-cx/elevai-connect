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
Billing Alarms Module

Creates AWS Budgets for cost monitoring and alerts.
"""

from typing import Dict, List
import pulumi
import pulumi_aws as aws


def create_billing_alarms(
    tags: Dict[str, str],
    alerting_infrastructure
) -> Dict[str, any]:
    """
    Create AWS Budgets for monitoring monthly spend.
    
    AWS Budgets must be created in us-east-1 region regardless of where
    other resources are deployed.
    
    Args:
        tags: Common tags to apply to resources
        alerting_infrastructure: AlertingInfrastructure instance for SNS topics
        
    Returns:
        Dictionary containing created budget resources and SNS topic
    """
    config = pulumi.Config("billing")
    
    # Check if billing alerts are enabled
    billing_enabled = config.get_bool("enabled")
    if not billing_enabled:
        pulumi.log.info("Billing alerts are disabled in configuration")
        return {"budgets": [], "topic": None}
    
    # Get configuration values
    monthly_limit = config.get_int("monthlyBudgetLimit")
    if not monthly_limit:
        raise ValueError("billing:monthlyBudgetLimit is required when billing:enabled is True")
    
    thresholds = config.get_object("alertThresholds") or [50, 80, 100]
    
    notification_email = config.get("notificationEmail")
    if not notification_email:
        raise ValueError("billing:notificationEmail is required when billing:enabled is True")
    
    resources = {"budgets": [], "topic": None}
    
    # Create SNS topic for budget notifications (must be in us-east-1)
    us_east_1_provider = aws.Provider(
        "us-east-1-provider",
        region="us-east-1"
    )
    
    budget_topic = aws.sns.Topic(
        "budget-alerts",
        display_name="AWS Budget Alerts",
        tags={
            **tags,
            "Name": "budget-alerts",
            "Description": "Notifications for AWS budget thresholds"
        },
        opts=pulumi.ResourceOptions(provider=us_east_1_provider)
    )
    
    # Subscribe email to budget topic
    aws.sns.TopicSubscription(
        "budget-alerts-email-subscription",
        topic=budget_topic.arn,
        protocol="email",
        endpoint=notification_email,
        opts=pulumi.ResourceOptions(provider=us_east_1_provider)
    )
    
    # Create budget notifications for each threshold
    notifications = []
    for threshold in thresholds:
        notifications.append({
            "comparison_operator": "GREATER_THAN",
            "notification_type": "ACTUAL",
            "threshold": threshold,
            "threshold_type": "PERCENTAGE",
            "subscriber_sns_topic_arns": [budget_topic.arn]
        })
        
        # Also add forecasted notifications for 100% threshold
        if threshold == 100:
            notifications.append({
                "comparison_operator": "GREATER_THAN",
                "notification_type": "FORECASTED",
                "threshold": threshold,
                "threshold_type": "PERCENTAGE",
                "subscriber_sns_topic_arns": [budget_topic.arn]
            })
    
    # Create the monthly budget
    # Note: AWS Budgets are global resources but API calls must go through us-east-1
    budget = aws.budgets.Budget(
        "monthly-spend-budget",
        budget_type="COST",
        limit_amount=str(monthly_limit),  # Convert to string for API
        limit_unit="USD",
        time_unit="MONTHLY",
        notifications=notifications,
        tags={
            **tags,
            "Name": "monthly-spend-budget",
        },
        opts=pulumi.ResourceOptions(provider=us_east_1_provider)
    )
    
    resources["budgets"].append(budget)
    resources["topic"] = budget_topic
    
    # Export budget information
    pulumi.export("budget_name", budget.id)
    pulumi.export("budget_limit", monthly_limit)
    pulumi.export("budget_topic_arn", budget_topic.arn)
    
    pulumi.log.info(f"Created monthly budget with ${monthly_limit} limit and thresholds at {thresholds}%")
    
    return resources
