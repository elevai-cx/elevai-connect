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
Amazon Q (QConnect) Integration

Main orchestration for Amazon Q integration with Amazon Connect.
"""

from typing import Dict, Any
import pulumi
import pulumi_aws as aws
import pulumi_command as command

from core.utils import create_secure_s3_bucket
from ..utils.naming import create_logical_name
from .knowledge_base import (
    create_assistant,
    create_data_integration,
    create_knowledge_base,
    associate_knowledge_base_with_assistant,
)
from .content_tagging import create_content_tagging_infrastructure


def create_qconnect_integration(
    connect_instance: aws.connect.Instance,
    knowledge_base_s3_bucket: aws.s3.Bucket,
    kms_key: aws.kms.Key,
    tags: Dict[str, str]
) -> Dict[str, Any]:
    """
    Create Amazon Q (QConnect) integration for Amazon Connect.
    
    This creates a complete Q integration including:
    - Wisdom Assistant (Q domain)
    - Knowledge Base with S3 data source
    - DataIntegration for automatic sync
    - Content tagging Lambda with SQS and EventBridge
    - Integration with Amazon Connect instance
    
    Args:
        connect_instance: Amazon Connect instance
        knowledge_base_s3_bucket: S3 bucket for knowledge base
        kms_key: KMS key for encryption
        tags: Tags to apply to resources
        
    Returns:
        Dictionary of created QConnect resources
    """
    config = pulumi.Config("qconnect")
    
    base_assistant_name = config.get("assistantName") or "q-assistant"
    base_kb_name = config.get("knowledgeBaseName") or "q-knowledge-base"
    base_integration_name = config.get("dataIntegrationName") or base_kb_name
    
    assistant_name = create_logical_name("qconnect", base_assistant_name)
    knowledge_base_name = create_logical_name("qconnect", base_kb_name)
    data_integration_name = create_logical_name("qconnect", base_integration_name)
    
    # Create Assistant
    assistant = create_assistant(assistant_name, kms_key, tags)

    # Create DataIntegration
    # The AppIntegrations bucket policy is now created as part of the bucket
    # itself (inside create_qconnect_knowledge_bucket) to avoid having two
    # competing BucketPolicy resources on the same bucket.
    data_integration = create_data_integration(
        data_integration_name,
        knowledge_base_s3_bucket,
        kms_key,
        tags,
    )
    
    # Create Knowledge Base
    knowledge_base = create_knowledge_base(
        knowledge_base_name,
        data_integration,
        kms_key,
        tags
    )
    
    # Associate Knowledge Base with Assistant
    assistant_association = associate_knowledge_base_with_assistant(
        assistant,
        knowledge_base,
        tags
    )
    
    # Integrate Assistant with Connect
    assistant_integration = command.local.Command(
        "q-assistant-integration",
        create=pulumi.Output.all(
            connect_instance.id,
            assistant.assistant_arn
        ).apply(
            lambda args: (
                f"aws connect create-integration-association "
                f"--instance-id {args[0]} "
                f"--integration-type WISDOM_ASSISTANT "
                f"--integration-arn {args[1]}"
            )
        ),
        delete=pulumi.Output.all(
            connect_instance.id,
            assistant.assistant_arn
        ).apply(
            lambda args: (
                f"aws connect list-integration-associations "
                f"--instance-id {args[0]} "
                f"--integration-type WISDOM_ASSISTANT "
                f"--query 'IntegrationAssociationSummaryList[?IntegrationArn==`{args[1]}`].IntegrationAssociationId' "
                f"--output text | xargs -I {{}} "
                f"aws connect delete-integration-association "
                f"--instance-id {args[0]} "
                f"--integration-association-id {{}}"
            )
        ),
        opts=pulumi.ResourceOptions(depends_on=[assistant, assistant_association]),
    )
    
    # Integrate Knowledge Base with Connect
    kb_integration = command.local.Command(
        "q-kb-integration",
        create=pulumi.Output.all(
            connect_instance.id,
            knowledge_base.knowledge_base_arn
        ).apply(
            lambda args: (
                f"aws connect create-integration-association "
                f"--instance-id {args[0]} "
                f"--integration-type WISDOM_KNOWLEDGE_BASE "
                f"--integration-arn {args[1]}"
            )
        ),
        delete=pulumi.Output.all(
            connect_instance.id,
            knowledge_base.knowledge_base_arn
        ).apply(
            lambda args: (
                f"aws connect list-integration-associations "
                f"--instance-id {args[0]} "
                f"--integration-type WISDOM_KNOWLEDGE_BASE "
                f"--query 'IntegrationAssociationSummaryList[?IntegrationArn==`{args[1]}`].IntegrationAssociationId' "
                f"--output text | xargs -I {{}} "
                f"aws connect delete-integration-association "
                f"--instance-id {args[0]} "
                f"--integration-association-id {{}}"
            )
        ),
        opts=pulumi.ResourceOptions(depends_on=[assistant_association]),
    )
    
    # Create content tagging infrastructure
    tagging_rules = config.get_object("contentTagging") or []
    content_tagging = create_content_tagging_infrastructure(
        knowledge_base,
        knowledge_base_s3_bucket,
        kms_key,
        tags,
        tagging_rules
    )
    
    # Exports
    pulumi.export("qconnect_assistant_id", assistant.assistant_id)
    pulumi.export("qconnect_assistant_arn", assistant.assistant_arn)
    pulumi.export("qconnect_knowledge_base_id", knowledge_base.knowledge_base_id)
    pulumi.export("qconnect_knowledge_base_arn", knowledge_base.knowledge_base_arn)
    pulumi.export("qconnect_kb_bucket", knowledge_base_s3_bucket.id)
    pulumi.export("qconnect_data_integration_arn", data_integration.data_integration_arn)
    pulumi.export("q_knowledge_tagging_function_name", 
                  content_tagging["lambda_function"].name)
    pulumi.export("q_knowledge_tagging_sqs_queue_url", 
                  content_tagging["sqs_queue"].url)
    pulumi.export("q_knowledge_tagging_dlq_url", 
                  content_tagging["dlq"].url)
    pulumi.export("qconnect_tagging_config_s3_uri", 
                  pulumi.Output.concat("s3://", knowledge_base_s3_bucket.id, 
                                     "/config/content-tagging/s3.json"))
    
    return {
        "assistant": assistant,
        "knowledge_base": knowledge_base,
        "assistant_association": assistant_association,
        "assistant_integration": assistant_integration,
        "kb_integration": kb_integration,
        **content_tagging
    }


def create_qconnect_knowledge_bucket(
    tags: Dict[str, str],
    kms_key: aws.kms.Key,
    logging_bucket: aws.s3.Bucket
) -> aws.s3.Bucket:
    """
    Create S3 bucket for QConnect knowledge base.

    Uses utility function for consistency with other buckets.
    Includes the AppIntegrations policy statements directly so there is
    a single BucketPolicy resource per bucket (AWS only allows one).

    Naming Pattern: <stage>-s3-<purpose>-<hash>
    Example: dev-s3-q-knowledge-abc123f

    Args:
        tags: Tags to apply
        kms_key: KMS key
        logging_bucket: Logging bucket

    Returns:
        S3 bucket for knowledge base
    """
    current = aws.get_caller_identity()
    region = aws.get_region()

    # AppIntegrations statements are included here rather than in a separate
    # BucketPolicy resource, because AWS only allows one policy per bucket.
    # Split into two statements so the sentinel ARN replacement in
    # create_secure_s3_bucket's build_policy works (it handles single-value
    # Resource fields: "arn:aws:s3:::*" → bucket ARN, "arn:aws:s3:::*/*" → objects).
    app_integrations_condition = {
        "StringEquals": {"aws:SourceAccount": current.account_id},
        "ArnEquals": {
            "aws:SourceArn": (
                f"arn:aws:app-integrations:{region.id}"
                f":{current.account_id}:data-integration/*"
            )
        },
    }
    app_integrations_statements = [
        {
            "Sid": "AllowAppIntegrationsListBucket",
            "Effect": "Allow",
            "Principal": {"Service": "app-integrations.amazonaws.com"},
            "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
            "Resource": "arn:aws:s3:::*",
            "Condition": app_integrations_condition,
        },
        {
            "Sid": "AllowAppIntegrationsGetObject",
            "Effect": "Allow",
            "Principal": {"Service": "app-integrations.amazonaws.com"},
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::*/*",
            "Condition": app_integrations_condition,
        },
    ]

    lifecycle_rules = [
        aws.s3.BucketLifecycleConfigurationRuleArgs(
            id="delete-old-versions",
            status="Enabled",
            noncurrent_version_expiration=aws.s3.BucketLifecycleConfigurationRuleNoncurrentVersionExpirationArgs(
                noncurrent_days=90,
            ),
        )
    ]

    logical_name = create_logical_name("s3", "q-knowledge")

    bucket = create_secure_s3_bucket(
        resource_name=logical_name,
        purpose="QConnectKnowledgeBase",
        tags=tags,
        kms_key=kms_key,
        logging_bucket=logging_bucket,
        lifecycle_rules=lifecycle_rules,
        additional_policy_statements=app_integrations_statements,
        # NO bucket_name parameter - let Pulumi add hash
    )

    return bucket
