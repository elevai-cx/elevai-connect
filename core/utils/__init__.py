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
Core Utilities Module

Reusable utility functions for AWS resource creation.
"""

from .s3 import create_secure_s3_bucket, create_logging_bucket
from .sqs import create_sqs_queue_with_dlq, create_sqs_queue
from .lambda_utils import create_lambda_with_requirements
from .iam import create_lambda_role
from .naming import (
    create_name,
    create_logical_name,
    get_stage,
    validate_length,
    get_limit,
    check_name_fits,
)

__all__ = [
    'create_secure_s3_bucket',
    'create_logging_bucket',
    'create_sqs_queue_with_dlq',
    'create_sqs_queue',
    'create_lambda_with_requirements',
    'create_lambda_role',
    'create_name',
    'create_logical_name',
    'get_stage',
    'validate_length',
    'get_limit',
    'check_name_fits',
]
