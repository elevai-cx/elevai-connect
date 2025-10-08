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
TEMPLATE: Resource Alarms

Copy this template when adding alarms for a new resource type.

Instructions:
1. Copy this file to core/<resource>_alarms.py
2. Replace RESOURCE with your resource name (e.g., 'sqs', 'lambda', 's3')
3. Replace METRIC examples with actual CloudWatch metrics for your resource
4. Update the namespace (e.g., 'AWS/Lambda', 'AWS/SQS', 'AWS/S3')
5. Define appropriate thresholds based on your resource's characteristics
6. Add documentation to get_RESOURCE_alarm_configs()
7. Import and call from core/__init__.py
"""

from typing import List, Dict
import pulumi_aws as aws

from .alerting import AlarmConfig, AlertingInfrastructure


def create_RESOURCE_alarms(
    resources: Dict[str, aws.RESOURCE.RESOURCE],
    alerting: AlertingInfrastructure
) -> None:
    """
    Create CloudWatch alarms for RESOURCE resources.
    
    This function defines all RESOURCE-related alarms and creates them
    through the alerting infrastructure.
    
    Args:
        resources: Dictionary of resource names to RESOURCE resources
        alerting: Alerting infrastructure instance
    """
    
    for resource_name, resource in resources.items():
        # Get the resource identifier (may need to use resource.name, resource.id, etc.)
        resource_id = resource.name
        
        # Example ERROR severity alarm
        # Use for critical failures requiring immediate attention
        alerting.create_alarm(AlarmConfig(
            name=f"RESOURCE-{resource_name}-critical-metric",
            description=f"RESOURCE {resource_name} critical metric exceeded",
            metric_name="MetricName",  # Replace with actual CloudWatch metric
            namespace="AWS/SERVICE",    # Replace with AWS namespace
            statistic="Sum",            # Sum, Average, Maximum, Minimum, SampleCount
            period=300,                 # 5 minutes (300 seconds)
            evaluation_periods=2,       # 2 consecutive periods
            threshold=10,               # Adjust threshold appropriately
            comparison_operator="GreaterThanThreshold",
            severity="ERROR",
            dimensions={"ResourceId": resource_id},  # Adjust dimension key
            treat_missing_data="notBreaching"
        ))
        
        # Example WARNING severity alarm
        # Use for issues that should be investigated but aren't critical
        alerting.create_alarm(AlarmConfig(
            name=f"RESOURCE-{resource_name}-warning-metric",
            description=f"RESOURCE {resource_name} warning metric exceeded",
            metric_name="AnotherMetricName",
            namespace="AWS/SERVICE",
            statistic="Average",
            period=300,
            evaluation_periods=2,
            threshold=75,  # Often use % or rate metrics
            comparison_operator="GreaterThanThreshold",
            severity="WARNING",
            dimensions={"ResourceId": resource_id},
            treat_missing_data="notBreaching"
        ))
        
        # Example INFO severity alarm
        # Use for capacity planning and informational alerts
        alerting.create_alarm(AlarmConfig(
            name=f"RESOURCE-{resource_name}-info-metric",
            description=f"RESOURCE {resource_name} info metric for capacity planning",
            metric_name="CapacityMetric",
            namespace="AWS/SERVICE",
            statistic="Maximum",
            period=300,
            evaluation_periods=1,
            threshold=100,
            comparison_operator="GreaterThanThreshold",
            severity="INFO",
            dimensions={"ResourceId": resource_id},
            treat_missing_data="notBreaching",
            datapoints_to_alarm=1  # Optional: require N of M datapoints
        ))


def get_RESOURCE_alarm_configs() -> List[dict]:
    """
    Get documentation for RESOURCE alarms.
    
    Returns a list of alarm configurations for documentation purposes.
    This helps developers understand what alarms are created.
    
    Returns:
        List of alarm configuration dictionaries with human-readable descriptions
    """
    return [
        {
            "name": "Critical Metric",
            "severity": "ERROR",
            "description": "Brief description of what triggers this alarm",
            "threshold": "Description of threshold (e.g., >10 errors in 10 minutes)",
            "action": "What to do when this alarm fires (investigation steps)"
        },
        {
            "name": "Warning Metric",
            "severity": "WARNING",
            "description": "Brief description of what triggers this alarm",
            "threshold": "Description of threshold",
            "action": "What to do when this alarm fires"
        },
        {
            "name": "Info Metric",
            "severity": "INFO",
            "description": "Brief description of what triggers this alarm",
            "threshold": "Description of threshold",
            "action": "What to do when this alarm fires"
        }
    ]


# ==============================================================================
# Integration Instructions
# ==============================================================================

"""
After creating this file, integrate it into your infrastructure:

1. Import in core/__init__.py:

   from .RESOURCE_alarms import create_RESOURCE_alarms

2. Call it in create_core_infrastructure():

   # Create RESOURCE resources
   RESOURCE_resources = create_RESOURCE_resources(tags, ...)
   resources["RESOURCE_resources"] = RESOURCE_resources
   
   # Later, in the alarm creation section:
   if RESOURCE_resources:
       create_RESOURCE_alarms(RESOURCE_resources, alerting)

3. Test your changes:

   pulumi preview  # Check for syntax errors
   pulumi up       # Deploy
   
   # Verify alarms in AWS Console → CloudWatch → Alarms

4. Document in ALERTING.md:

   Add your alarms to the "Current Alarms" section with a table
   showing alarm names, severities, thresholds, and descriptions.
"""

# ==============================================================================
# Choosing the Right Metrics
# ==============================================================================

"""
When selecting metrics for your alarms, consider:

ERROR Severity (Critical - Immediate Action Required):
- Service failures or errors
- Throttling or rate limiting
- Data loss risks
- Service unavailability
- Security issues

WARNING Severity (Investigate Soon):
- Performance degradation
- Approaching limits
- Retryable errors
- Configuration issues
- Resource constraints

INFO Severity (Awareness / Capacity Planning):
- Usage trends
- High but acceptable utilization
- Capacity approaching planned limits
- Informational state changes

Common CloudWatch Metrics by Service:
- Lambda: Errors, Throttles, Duration, ConcurrentExecutions
- DynamoDB: ReadThrottleEvents, WriteThrottleEvents, UserErrors
- SQS: ApproximateAgeOfOldestMessage, ApproximateNumberOfMessagesVisible
- SNS: NumberOfNotificationsFailed, NumberOfMessagesPublished
- API Gateway: 4XXError, 5XXError, Latency, Count
- S3: 4xxErrors, 5xxErrors, BucketSizeBytes
- Connect: ConcurrentCalls, MissedCalls, ContactFlowErrors

Find metrics for your service:
https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/aws-services-cloudwatch-metrics.html
"""

# ==============================================================================
# Best Practices
# ==============================================================================

"""
1. Start Conservative
   - Begin with ERROR alarms only
   - Add WARNING/INFO after understanding baseline

2. Use Meaningful Thresholds
   - Base on actual usage patterns, not guesses
   - Review and adjust after collecting data
   - Consider using percentiles for latency metrics

3. Avoid Alert Fatigue
   - Too many false positives = ignored alarms
   - Use appropriate evaluation_periods
   - Set treat_missing_data appropriately

4. Clear Descriptions
   - Explain what the alarm means
   - Include remediation steps
   - Reference documentation if complex

5. Appropriate Severity
   - ERROR: Wakes someone up at 3 AM
   - WARNING: Review during business hours
   - INFO: Useful for reports and trends

6. Test Your Alarms
   - Manually trigger conditions if possible
   - Verify notifications are received
   - Validate remediation steps work

7. Monitor Alarm Health
   - Review alarm states regularly
   - Check for alarms stuck in ALARM state
   - Remove or adjust noisy alarms

8. Document Everything
   - Add to get_RESOURCE_alarm_configs()
   - Update ALERTING.md
   - Include in CONTRIBUTING.md if applicable
"""
