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
Amazon Connect Instance Validation

Validation utilities for Connect instance configuration.
"""

import re
import pulumi


def validate_instance_alias(alias: str) -> None:
    """
    Validate the Amazon Connect instance alias format.
    
    Requirements:
    - 1-64 characters
    - Starts with a letter
    - Only lowercase letters, numbers, and hyphens
    - Cannot end with hyphen or have consecutive hyphens
    - Recommended pattern: name-region-env
    
    Args:
        alias: The instance alias to validate
        
    Raises:
        ValueError: If the alias doesn't meet requirements
    """
    if not alias:
        raise ValueError("Instance alias cannot be empty")
    
    if len(alias) < 1 or len(alias) > 64:
        raise ValueError(
            f"Instance alias must be between 1 and 64 characters. Got: {len(alias)}"
        )
    
    if not alias[0].isalpha():
        raise ValueError(f"Instance alias must start with a letter. Got: '{alias}'")
    
    if not re.match(r'^[a-z0-9-]+$', alias):
        raise ValueError(
            f"Instance alias can only contain lowercase letters, numbers, "
            f"and hyphens. Got: '{alias}'"
        )
    
    if alias.endswith('-'):
        raise ValueError(f"Instance alias cannot end with a hyphen. Got: '{alias}'")
    
    if '--' in alias:
        raise ValueError(
            f"Instance alias cannot contain consecutive hyphens. Got: '{alias}'"
        )
    
    # Warning about common format issues
    _check_alias_pattern(alias)


def _check_alias_pattern(alias: str) -> None:
    """Check for common alias pattern issues and warn if found."""
    parts = alias.split('-')
    if len(parts) < 3:
        return
    
    last_part = parts[-1]
    second_last = parts[-2] if len(parts) >= 2 else ""
    
    env_names = ['dev', 'test', 'staging', 'prod', 'production']
    region_abbrevs = ['euw1', 'euw2', 'euw3', 'use1', 'use2', 'usw1', 'usw2']
    
    if second_last in env_names and last_part in region_abbrevs:
        suggested = '-'.join(parts[:-2] + [last_part, second_last])
        pulumi.log.warn(
            f"Instance alias '{alias}' uses pattern 'name-env-region'. "
            f"This format has been known to fail. "
            f"Consider using 'name-region-env' instead: '{suggested}'"
        )