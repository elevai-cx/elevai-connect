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
Amazon Connect Infrastructure Module

Provides functions for creating and configuring Amazon Connect instances.
"""

from .instance import create_connect_instance
from .validation import validate_instance_alias
from .s3 import create_s3_buckets
from .iam import create_iam_resources

__all__ = [
    'create_connect_instance',
    'validate_instance_alias',
    'create_s3_buckets',
    'create_iam_resources',
]