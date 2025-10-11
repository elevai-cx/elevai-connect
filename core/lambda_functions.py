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
Lambda Functions for Amazon Connect

Creates Connect-specific Lambda functions using reusable utilities.
"""

from typing import Dict
import pulumi_aws as aws

from .utils import create_lambda_with_requirements


def create_lambda_functions(
    connect_instance: aws.connect.Instance,
    iam_role: aws.iam.Role,
    tags: Dict[str, str]
) -> Dict[str, aws.lambda_.Function]:
    """
    Create Lambda functions for Amazon Connect integrations.
    
    Uses utility functions for consistent configuration.
    
    Args:
        connect_instance: Amazon Connect instance
        iam_role: IAM role for Lambda execution
        tags: Tags to apply to functions
        
    Returns:
        Dictionary of function names to Lambda resources
    """
    functions = {}
    
    # Utils function - common utilities for contact flows
    utils_function = create_lambda_with_requirements(
        name="utils",
        lambda_dir="./lambda-code/utils",
        iam_role=iam_role,
        tags=tags,
        memory_size=512,
        timeout=7,
        connect_instance=connect_instance,
    )
    functions["utils"] = utils_function
    
    return functions
