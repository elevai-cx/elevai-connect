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
Amazon Q Knowledge Base Management

Handles creation of Assistant, Knowledge Base, and DataIntegration resources.
"""

from typing import Dict
import json
import pulumi
import pulumi_aws as aws
import pulumi_aws_native as aws_native


def create_assistant(
    name: str,
    kms_key: aws.kms.Key,
    tags: Dict[str, str]
) -> aws_native.wisdom.Assistant:
    """
    Create Amazon Q Assistant (Wisdom domain).
    
    Name should include stage prefix for consistency.
    Example: dev-q-assistant
    
    Args:
        name: Assistant name (with stage prefix)
        kms_key: KMS key for encryption
        tags: Tags to apply
        
    Returns:
        Wisdom Assistant resource
    """
    assistant = aws_native.wisdom.Assistant(
        "q-assistant",
        name=name,
        type="AGENT",
        description="Amazon Q assistant for Amazon Connect agents",
        server_side_encryption_configuration={
            "kmsKeyId": kms_key.arn,
        },
        tags=[
            {"key": key, "value": value}
            for key, value in {**tags, "Name": name}.items()
        ],
        opts=pulumi.ResourceOptions(
            # Amazon Connect manages additional tags on Wisdom resources
            # outside of Pulumi. Ignore tag diffs to prevent unnecessary
            # replacements which break integration associations.
            ignore_changes=["tags"],
            retain_on_delete=True,
        ),
    )
    
    return assistant


def create_data_integration(
    name: str,
    bucket: aws.s3.Bucket,
    kms_key: aws.kms.Key,
    tags: Dict[str, str],
    opts: pulumi.ResourceOptions = None
) -> aws_native.appintegrations.DataIntegration:
    """
    Create DataIntegration for S3 bucket.
    
    Name should include stage prefix for consistency.
    Example: dev-q-data-integration
    
    Args:
        name: Integration name (with stage prefix)
        bucket: S3 bucket
        kms_key: KMS key
        tags: Tags to apply
        
    Returns:
        DataIntegration resource
    """
    data_integration = aws_native.appintegrations.DataIntegration(
        "qconnect-s3-integration",
        name=name,
        description=" ",
        kms_key=kms_key.arn,
        source_uri=bucket.bucket.apply(
            lambda bucket_name: f"s3://{bucket_name}"
        ),
        tags=[
            {"key": key, "value": value}
            for key, value in {**tags, "Name": name}.items()
        ],
        opts=opts,
    )
    
    return data_integration


def create_knowledge_base(
    name: str,
    data_integration: aws_native.appintegrations.DataIntegration,
    kms_key: aws.kms.Key,
    tags: Dict[str, str]
) -> aws_native.wisdom.KnowledgeBase:
    """
    Create Amazon Q Knowledge Base.
    
    Name should include stage prefix for consistency.
    Example: dev-q-knowledge-base
    
    Args:
        name: Knowledge base name (with stage prefix)
        data_integration: DataIntegration resource
        kms_key: KMS key
        tags: Tags to apply
        
    Returns:
        Knowledge Base resource
    """
    knowledge_base = aws_native.wisdom.KnowledgeBase(
        "q-knowledge-base",
        name=name,
        knowledge_base_type="EXTERNAL",
        description="Knowledge base for Amazon Q with S3 data source",
        source_configuration={
            "appIntegrations": {
                "appIntegrationArn": data_integration.data_integration_arn,
            },
        },
        server_side_encryption_configuration={
            "kmsKeyId": kms_key.arn,
        },
        tags=[
            {"key": key, "value": value}
            for key, value in {**tags, "Name": name}.items()
        ],
        opts=pulumi.ResourceOptions(
            # Amazon Connect manages additional tags on Wisdom resources
            # outside of Pulumi. Ignore tag diffs to prevent unnecessary
            # replacements which break integration associations.
            ignore_changes=["tags"],
            retain_on_delete=True,
        ),
    )
    
    return knowledge_base


def associate_knowledge_base_with_assistant(
    assistant: aws_native.wisdom.Assistant,
    knowledge_base: aws_native.wisdom.KnowledgeBase,
    tags: Dict[str, str]
) -> aws_native.wisdom.AssistantAssociation:
    """
    Associate Knowledge Base with Assistant.
    
    Args:
        assistant: Assistant resource
        knowledge_base: Knowledge Base resource
        tags: Tags to apply
        
    Returns:
        Assistant Association resource
    """
    association = aws_native.wisdom.AssistantAssociation(
        "q-assistant-kb-association",
        assistant_id=assistant.assistant_id,
        association={
            "knowledgeBaseId": knowledge_base.knowledge_base_id,
        },
        association_type="KNOWLEDGE_BASE",
        tags=[
            {"key": key, "value": value}
            for key, value in tags.items()
        ],
        opts=pulumi.ResourceOptions(
            ignore_changes=["tags"],
            retain_on_delete=True,
        ),
    )
    
    return association


def create_bucket_policy_for_app_integrations(
    bucket: aws.s3.Bucket
) -> aws.s3.BucketPolicy:
    """
    Create bucket policy allowing AppIntegrations service access.
    
    Args:
        bucket: S3 bucket
        
    Returns:
        Bucket policy resource
    """
    current = aws.get_caller_identity()
    region = aws.get_region()
    
    bucket_policy = aws.s3.BucketPolicy(
        "qconnect-s3-bucket-policy",
        bucket=bucket.id,
        policy=pulumi.Output.all(
            bucket.arn,
            current.account_id,
            region.id 
        ).apply(
            lambda args: json.dumps({
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "AllowAppIntegrationsDataIntegrations",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "app-integrations.amazonaws.com"
                        },
                        "Action": [
                            "s3:ListBucket",
                            "s3:GetObject",
                            "s3:GetBucketLocation"
                        ],
                        "Resource": [
                            args[0],
                            f"{args[0]}/*"
                        ],
                        "Condition": {
                            "StringEquals": {
                                "aws:SourceAccount": args[1]
                            },
                            "ArnEquals": {
                                "aws:SourceArn": f"arn:aws:app-integrations:{args[2]}:{args[1]}:data-integration/*"
                            }
                        }
                    },
                    {
                        "Sid": "RequireSSL",
                        "Effect": "Deny",
                        "Principal": "*",
                        "Action": "s3:*",
                        "Resource": [
                            args[0],
                            f"{args[0]}/*"
                        ],
                        "Condition": {
                            "Bool": {
                                "aws:SecureTransport": "false"
                            }
                        }
                    }
                ]
            })
        ),
    )
    
    return bucket_policy
