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
Alarm Configuration Utilities

Helper functions for reading alarm configuration from Pulumi config.
"""

from typing import Any, Optional, Dict
import pulumi


def get_alarm_config(
    resource_type: str,
    alarm_name: str,
    setting: str,
    default: Any
) -> Any:
    """
    Get alarm configuration value with fallback to default.
    
    Reads from nested configuration structure:
    alarms:
      {resource_type}:
        {alarm_name}:
          {setting}: value
    
    Or for single-level settings:
    alarms:
      {resource_type}:
        {alarm_name}: value
    
    Args:
        resource_type: Resource type (lambda, dynamodb, connect, sqs)
        alarm_name: Name of the alarm (errors, throttles, etc.)
        setting: Setting name (threshold, period, evaluationPeriods)
        default: Default value if not configured
        
    Returns:
        Configuration value or default
        
    Examples:
        get_alarm_config("lambda", "errors", "threshold", 5)
        # Reads: alarms.lambda.errors.threshold, returns 5 if not set
        
        get_alarm_config("connect", "concurrentPercentageWarning", "", 80)
        # Reads: alarms.connect.concurrentPercentageWarning, returns 80 if not set
    """
    config = pulumi.Config("alarms")
    
    try:
        # Get the resource type object (e.g., lambda, dynamodb, connect)
        resource_config = config.get_object(resource_type)
        
        if resource_config is None:
            return default
        
        # If no alarm_name, the setting is directly under resource_type
        if not alarm_name:
            if setting and isinstance(resource_config, dict):
                return resource_config.get(setting, default)
            return default
        
        # Get the alarm object (e.g., errors, throttles)
        if not isinstance(resource_config, dict):
            return default
            
        alarm_config = resource_config.get(alarm_name)
        
        if alarm_config is None:
            return default
        
        # If no setting specified, return the alarm_config value directly
        if not setting:
            return alarm_config if alarm_config is not None else default
        
        # Get the specific setting (threshold, period, evaluationPeriods)
        if isinstance(alarm_config, dict):
            return alarm_config.get(setting, default)
        
        return default
        
    except Exception:
        # If any error occurs reading config, return default
        return default


def get_alarm_threshold(resource_type: str, alarm_name: str, default: int) -> int:
    """Get alarm threshold with default."""
    return get_alarm_config(resource_type, alarm_name, "threshold", default)


def get_alarm_period(resource_type: str, alarm_name: str, default: int) -> int:
    """Get alarm period with default."""
    return get_alarm_config(resource_type, alarm_name, "period", default)


def get_alarm_evaluation_periods(
    resource_type: str,
    alarm_name: str,
    default: int
) -> int:
    """Get alarm evaluation periods with default."""
    return get_alarm_config(resource_type, alarm_name, "evaluationPeriods", default)
