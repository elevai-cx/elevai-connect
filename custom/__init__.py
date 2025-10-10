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
Custom Resources Module

This module is designed for your custom extensions and modifications.
Add your own infrastructure components here without worrying about conflicts
when updating core resources from the upstream repository.
"""

from typing import Dict, Any


def initialize_custom_resources(
    core_resources: Dict[str, Any],
    tags: Dict[str, str]
) -> Dict[str, Any]:
    """
    Initialize custom resources and extensions.
    
    This function is called after core infrastructure is created.
    Add your custom resource creation here.
    
    Args:
        core_resources: Dictionary of core resources (Connect instance, DynamoDB tables, etc.)
        tags: Common tags to apply to resources
        
    Returns:
        Dictionary containing references to custom resources
    """
    custom_resources = {}
    
    # Example: Access core resources
    # connect_instance = core_resources.get("connect_instance")
    # dynamodb_tables = core_resources.get("dynamodb_tables")
    
    # Add your custom resources here
    # custom_resources["my_feature"] = create_my_feature(connect_instance, tags)
    
    return custom_resources


__all__ = ["initialize_custom_resources"]
