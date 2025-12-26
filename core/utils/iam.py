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
IAM Utilities

Reusable IAM role and policy creation functions.

Naming Convention:
- IAM Role: <stage>-iam-role-<purpose> (64 char limit)
- IAM Policy: <stage>-iam-policy-<purpose> (128 char limit)
"""

from typing import Dict, Optional, List, Union
import json
import pulumi
import pulumi_aws as aws

from .naming import create_name, create_logical_name


def create_lambda_role(
    purpose: str,
    tags: Dict[str, str],
    additional_policy_statements: Optional[Union[List[Dict], pulumi.Output]] = None,
    managed_policy_arns: Optional[List[str]] = None,
) -> tuple[aws.iam.Role, List[aws.iam.RolePolicyAttachment]]:
    """
    Create an IAM role for Lambda with basic execution permissions.
    
    Naming convention:
    - Role: <stage>-iam-role-<purpose>
    - Policy: <stage>-iam-policy-<purpose>
    
    Examples:
    - dev-iam-role-lambda-execution
    - dev-iam-policy-lambda-custom
    
    Always includes:
    - AWSLambdaBasicExecutionRole (CloudWatch Logs)
    - AWSXRayDaemonWriteAccess (X-Ray tracing)
    
    Args:
        purpose: Descriptive purpose (e.g., 'lambda-execution', 'knowledge-tagging')
        tags: Tags to apply to the role
        additional_policy_statements: Optional additional policy statements
        managed_policy_arns: Optional additional managed policy ARNs
        
    Returns:
        Tuple of (IAM role, list of policy attachments)
    """
    # Generate standardized names
    role_name = create_name("iam-role", purpose)
    role_logical = create_logical_name("iam-role", purpose)
    
    role = aws.iam.Role(
        role_logical,
        name=role_name,
        assume_role_policy="""{
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "sts:AssumeRole",
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                }
            }]
        }""",
        tags={**tags, "Name": role_name},
    )
    
    policy_attachments = []
    
    # Attach basic execution role
    basic_exec = aws.iam.RolePolicyAttachment(
        f"{role_logical}-basic-execution",
        role=role.name,
        policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    )
    policy_attachments.append(basic_exec)
    
    # Attach X-Ray permissions
    xray = aws.iam.RolePolicyAttachment(
        f"{role_logical}-xray",
        role=role.name,
        policy_arn="arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess",
    )
    policy_attachments.append(xray)
    
    # Attach additional managed policies
    if managed_policy_arns:
        for idx, policy_arn in enumerate(managed_policy_arns):
            attachment = aws.iam.RolePolicyAttachment(
                f"{role_logical}-managed-{idx}",
                role=role.name,
                policy_arn=policy_arn,
            )
            policy_attachments.append(attachment)
    
    # Create and attach custom policy if statements provided
    if additional_policy_statements is not None:
        policy_name = create_name("iam-policy", purpose)
        policy_logical = create_logical_name("iam-policy", purpose)
        
        # Handle both raw list and Pulumi Output
        if isinstance(additional_policy_statements, pulumi.Output):
            # It's a Pulumi Output - apply the serialization
            policy_document = additional_policy_statements.apply(
                lambda statements: json.dumps({
                    "Version": "2012-10-17",
                    "Statement": statements
                })
            )
        else:
            # It's a raw list - serialize directly
            policy_document = json.dumps({
                "Version": "2012-10-17",
                "Statement": additional_policy_statements
            })
        
        policy = aws.iam.Policy(
            policy_logical,
            name=policy_name,
            description=f"Custom policy for {purpose}",
            policy=policy_document,
            tags={**tags, "Name": policy_name},
        )
        
        custom_attachment = aws.iam.RolePolicyAttachment(
            f"{role_logical}-custom-policy",
            role=role.name,
            policy_arn=policy.arn,
        )
        policy_attachments.append(custom_attachment)
    
    return role, policy_attachments
