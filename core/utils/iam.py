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
"""

from typing import Dict, Optional, List, Union
import json
import pulumi
import pulumi_aws as aws


def create_lambda_role(
    resource_name: str,
    tags: Dict[str, str],
    additional_policy_statements: Optional[Union[List[Dict], pulumi.Output]] = None,
    managed_policy_arns: Optional[List[str]] = None,
) -> tuple[aws.iam.Role, List[aws.iam.RolePolicyAttachment]]:
    """
    Create an IAM role for Lambda with basic execution permissions.
    
    Always includes:
    - AWSLambdaBasicExecutionRole (CloudWatch Logs)
    - AWSXRayDaemonWriteAccess (X-Ray tracing)
    
    Args:
        resource_name: Pulumi resource name
        tags: Tags to apply to the role
        additional_policy_statements: Optional additional policy statements
        managed_policy_arns: Optional additional managed policy ARNs
        
    Returns:
        Tuple of (IAM role, list of policy attachments)
    """
    role = aws.iam.Role(
        resource_name,
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
        tags={**tags, "Name": resource_name},
    )
    
    policy_attachments = []
    
    # Attach basic execution role
    basic_exec = aws.iam.RolePolicyAttachment(
        f"{resource_name}-basic-execution",
        role=role.name,
        policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    )
    policy_attachments.append(basic_exec)
    
    # Attach X-Ray permissions
    xray = aws.iam.RolePolicyAttachment(
        f"{resource_name}-xray",
        role=role.name,
        policy_arn="arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess",
    )
    policy_attachments.append(xray)
    
    # Attach additional managed policies
    if managed_policy_arns:
        for idx, policy_arn in enumerate(managed_policy_arns):
            attachment = aws.iam.RolePolicyAttachment(
                f"{resource_name}-managed-{idx}",
                role=role.name,
                policy_arn=policy_arn,
            )
            policy_attachments.append(attachment)
    
    # Create and attach custom policy if statements provided
    if additional_policy_statements is not None:
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
            f"{resource_name}-policy",
            description=f"Custom policy for {resource_name}",
            policy=policy_document,
            tags=tags,
        )
        
        custom_attachment = aws.iam.RolePolicyAttachment(
            f"{resource_name}-custom-policy",
            role=role.name,
            policy_arn=policy.arn,
        )
        policy_attachments.append(custom_attachment)
    
    return role, policy_attachments
