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
Configuration Module

Shared settings and configuration utilities for the project.
"""

import pulumi
from typing import Any, Optional


class Settings:
    """
    Centralized settings management for the Pulumi project.
    """
    
    def __init__(self):
        self.config = pulumi.Config()
        self.aws_config = pulumi.Config("aws")
        self.connect_config = pulumi.Config("connect")
        self.dynamodb_config = pulumi.Config("dynamodb")
        
        # Project metadata
        self.project_name = pulumi.get_project()
        self.stack_name = pulumi.get_stack()
        self.region = self.aws_config.get("region") or "us-east-1"
        
    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Get a configuration value with optional default."""
        return self.config.get(key) or default
    
    def require(self, key: str) -> Any:
        """Get a required configuration value."""
        return self.config.require(key)
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean configuration value."""
        return self.config.get_bool(key) or default
    
    @property
    def resource_prefix(self) -> str:
        """Get the resource naming prefix."""
        return f"{self.project_name}-{self.stack_name}"


# Global settings instance
settings = Settings()


__all__ = ["settings", "Settings"]
