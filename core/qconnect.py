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
Amazon Q (Wisdom) Integration for Amazon Connect

This module creates Amazon Q (formerly Amazon Connect Wisdom) resources
and integrates them with Amazon Connect. Amazon Q provides AI-powered
knowledge management and recommendations for contact center agents.

Note: This module uses pulumi_aws_native because Amazon Q resources
are not fully supported in the standard pulumi_aws provider.

IMPORTANT: For S3-based knowledge bases with automatic sync:
- Knowledge Base Type: EXTERNAL (enables automatic sync)
- DataIntegration: Points to S3 bucket with no scheduleConfig
- Assistant Integration: Requires SNS topic for event notifications
- Files uploaded to S3 are automatically ingested into the knowledge base
- Content Tagging: EventBridge rules trigger SQS queue, which batches events to Lambda
"""

from typing import Dict, Any
import json
import pulumi
import pulumi_aws as aws
import pulumi_aws_native as aws_native
import pulumi_command as command
from core.lambda_functions import create_lambda_with_requirements


def create_qconnect_integration(
    connect_instance: aws.connect.Instance,
    knowledge_base_s3_bucket: aws.s3.Bucket,
    kms_key: aws.kms.Key,
    tags: Dict[str, str]
) -> Dict[str, Any]:
    """
    Create Amazon Q (QConnect) integration for Amazon Connect.
    
    This creates:
    - A Wisdom Assistant (Q domain)
    - A Knowledge Base with S3 as the data source
    - Integration with the Amazon Connect instance
    - Content tagging Lambda function for automatic tagging
    - SQS queue with DLQ for reliable event processing
    - EventBridge rules to trigger SQS on .json file events
    - Automatic upload of tagging configuration to S3
    
    All data is encrypted using the customer-managed KMS key.
    
    Args:
        connect_instance: The Amazon Connect instance to integrate with
        knowledge_base_s3_bucket: S3 bucket containing knowledge base data and config
        kms_key: KMS key for encryption
        lambda_role: IAM role for Lambda execution
        tags: Tags to apply to resources
        
    Returns:
        Dictionary containing references to created QConnect resources
    """
    config = pulumi.Config("qconnect")
    
    # Get configuration
    assistant_name = config.get("assistantName") or "connect-q-assistant"
    knowledge_base_name = config.get("knowledgeBaseName") or "connect-knowledge-base"
    
    # Create the Wisdom Assistant (Q domain)
    assistant = aws_native.wisdom.Assistant(
        "q-assistant",
        name=assistant_name,
        type="AGENT",
        description="Amazon Q assistant for Amazon Connect agents",
        server_side_encryption_configuration={
            "kmsKeyId": kms_key.arn,
        },
        tags=[
            {"key": key, "value": value}
            for key, value in {**tags, "Name": assistant_name}.items()
        ],
    )
    
    # Get AWS account and region for bucket policy
    current = aws.get_caller_identity()
    region = aws.get_region()
    
    # Create bucket policy allowing AppIntegrations service and requiring SSL
    bucket_policy = aws.s3.BucketPolicy(
        "qconnect-s3-bucket-policy",
        bucket=knowledge_base_s3_bucket.id,
        policy=pulumi.Output.all(
            knowledge_base_s3_bucket.arn,
            current.account_id,
            region.id 
        ).apply(
            lambda args: f"""{{
                "Version": "2012-10-17",
                "Statement": [
                    {{
                        "Sid": "AllowAppIntegrationsDataIntegrations",
                        "Effect": "Allow",
                        "Principal": {{
                            "Service": "app-integrations.amazonaws.com"
                        }},
                        "Action": [
                            "s3:ListBucket",
                            "s3:GetObject",
                            "s3:GetBucketLocation"
                        ],
                        "Resource": [
                            "{args[0]}",
                            "{args[0]}/*"
                        ],
                        "Condition": {{
                            "StringEquals": {{
                                "aws:SourceAccount": "{args[1]}"
                            }},
                            "ArnEquals": {{
                                "aws:SourceArn": "arn:aws:app-integrations:{args[2]}:{args[1]}:data-integration/*"
                            }}
                        }}
                    }},
                    {{
                        "Sid": "RequireSSL",
                        "Effect": "Deny",
                        "Principal": "*",
                        "Action": "s3:*",
                        "Resource": [
                            "{args[0]}",
                            "{args[0]}/*"
                        ],
                        "Condition": {{
                            "Bool": {{
                                "aws:SecureTransport": "false"
                            }}
                        }}
                    }}
                ]
            }}"""
        ),
    )
    
    # Create the DataIntegration for S3
    data_integration = aws_native.appintegrations.DataIntegration(
        "qconnect-s3-integration",
        name=knowledge_base_name,
        description=" ",
        kms_key=kms_key.arn,
        source_uri=knowledge_base_s3_bucket.bucket.apply(
            lambda bucket_name: f"s3://{bucket_name}"
        ),
        tags=[
            {"key": key, "value": value}
            for key, value in {**tags, "Name": knowledge_base_name}.items()
        ],
        opts=pulumi.ResourceOptions(depends_on=[bucket_policy]),
    )
    
    # Create the Knowledge Base
    knowledge_base = aws_native.wisdom.KnowledgeBase(
        "q-knowledge-base",
        name=knowledge_base_name,
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
            for key, value in {**tags, "Name": knowledge_base_name}.items()
        ],
    )
    
    # Associate the Knowledge Base with the Assistant
    assistant_association = aws_native.wisdom.AssistantAssociation(
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
    )
    
    # Integrate Assistant with Amazon Connect
    assistant_integration = command.local.Command(
        "q-assistant-integration",
        create=pulumi.Output.all(
            connect_instance.id,
            assistant.assistant_arn
        ).apply(
            lambda args: f"aws connect create-integration-association --instance-id {args[0]} --integration-type WISDOM_ASSISTANT --integration-arn {args[1]}"
        ),
        delete=pulumi.Output.all(
            connect_instance.id,
            assistant.assistant_arn
        ).apply(
            lambda args: f"aws connect list-integration-associations --instance-id {args[0]} --integration-type WISDOM_ASSISTANT --query 'IntegrationAssociationSummaryList[?IntegrationArn==`{args[1]}`].IntegrationAssociationId' --output text | xargs -I {{}} aws connect delete-integration-association --instance-id {args[0]} --integration-association-id {{}}"
        ),
        opts=pulumi.ResourceOptions(
            depends_on=[assistant, assistant_association]
        ),
    )
    
    # Integrate Knowledge Base with Amazon Connect
    kb_integration = command.local.Command(
        "q-kb-integration",
        create=pulumi.Output.all(
            connect_instance.id,
            knowledge_base.knowledge_base_arn
        ).apply(
            lambda args: f"aws connect create-integration-association --instance-id {args[0]} --integration-type WISDOM_KNOWLEDGE_BASE --integration-arn {args[1]}"
        ),
        delete=pulumi.Output.all(
            connect_instance.id,
            knowledge_base.knowledge_base_arn
        ).apply(
            lambda args: f"aws connect list-integration-associations --instance-id {args[0]} --integration-type WISDOM_KNOWLEDGE_BASE --query 'IntegrationAssociationSummaryList[?IntegrationArn==`{args[1]}`].IntegrationAssociationId' --output text | xargs -I {{}} aws connect delete-integration-association --instance-id {args[0]} --integration-association-id {{}}"
        ),
        opts=pulumi.ResourceOptions(
            depends_on=[assistant_association]
        ),
    )
    
    # Generate tagging configuration from Pulumi config
    tagging_rules = config.get_object("contentTagging") or []
    
    # Convert to the expected JSON structure
    tagging_config = {
        "taggingRules": tagging_rules
    }
    
    # Upload generated tagging configuration to S3
    config_object = aws.s3.BucketObjectv2(
        "q-tagging-config",
        bucket=knowledge_base_s3_bucket.id,
        key="config/content-tagging/s3.json",
        content=json.dumps(tagging_config, indent=2),
        content_type="application/json",
        tags={**tags, "Purpose": "ContentTaggingConfig"},
    )
    
    # Enable EventBridge notifications for the S3 bucket
    aws.s3.BucketNotification(
        "q-knowledge-bucket-eventbridge",
        bucket=knowledge_base_s3_bucket.id,
        eventbridge=True,
    )
    
    # Create SQS queues (DLQ first, then main queue)
    sqs_queues = create_content_tagger_sqs_queues(kms_key, tags)
    
    # Create Content Tagger Lambda
    content_tagger_role, role_policy_attachments = create_content_tagger_iam_role(
        knowledge_base_s3_bucket,
        kms_key,
        sqs_queues["main_queue"],
        sqs_queues["dlq"],
        tags
    )
    
    content_tagger = create_lambda_with_requirements(
        name="content-tagger",
        lambda_dir="./lambda-code/content-tagger",
        iam_role=content_tagger_role,
        tags=tags,
        memory_size=512,
        timeout=60,
        environment_variables={
            "KNOWLEDGE_BASE_ID": knowledge_base.knowledge_base_id,
            "CONFIG_BUCKET": knowledge_base_s3_bucket.id,
            "CONFIG_KEY": "config/content-tagging/s3.json",
        },
        opts=pulumi.ResourceOptions(depends_on=role_policy_attachments),
    )
    
    # Configure Lambda to process SQS messages with 30s batch window
    event_source_mapping = aws.lambda_.EventSourceMapping(
        "content-tagger-sqs-trigger",
        event_source_arn=sqs_queues["main_queue"].arn,
        function_name=content_tagger.name,
        batch_size=10,
        maximum_batching_window_in_seconds=30,
        function_response_types=["ReportBatchItemFailures"],
        opts=pulumi.ResourceOptions(depends_on=[content_tagger]),
    )
    
    # Create EventBridge rules for .json files routing to SQS
    eventbridge_rules = create_content_tagger_eventbridge_rules(
        knowledge_base_s3_bucket,
        sqs_queues["main_queue"],
        tags
    )
    
    # Export important values
    pulumi.export("qconnect_assistant_id", assistant.assistant_id)
    pulumi.export("qconnect_assistant_arn", assistant.assistant_arn)
    pulumi.export("qconnect_knowledge_base_id", knowledge_base.knowledge_base_id)
    pulumi.export("qconnect_knowledge_base_arn", knowledge_base.knowledge_base_arn)
    pulumi.export("qconnect_kb_bucket", knowledge_base_s3_bucket.id)
    pulumi.export("qconnect_data_integration_arn", data_integration.data_integration_arn)
    pulumi.export("content_tagger_function_name", content_tagger.name)
    pulumi.export("content_tagger_sqs_queue_url", sqs_queues["main_queue"].url)
    pulumi.export("content_tagger_dlq_url", sqs_queues["dlq"].url)
    pulumi.export("qconnect_tagging_config_s3_uri", 
        pulumi.Output.concat("s3://", knowledge_base_s3_bucket.id, "/config/content-tagging/s3.json")
    )
    
    return {
        "assistant": assistant,
        "knowledge_base": knowledge_base,
        "assistant_association": assistant_association,
        "assistant_integration": assistant_integration,
        "kb_integration": kb_integration,
        "content_tagger": content_tagger,
        "sqs_queue": sqs_queues["main_queue"],
        "dlq": sqs_queues["dlq"],
        "event_source_mapping": event_source_mapping,
        "eventbridge_rules": eventbridge_rules,
        "tagging_config": config_object,
    }


def create_content_tagger_sqs_queues(
    kms_key: aws.kms.Key,
    tags: Dict[str, str]
) -> Dict[str, aws.sqs.Queue]:
    """
    Create SQS queues for content tagger Lambda.
    
    Creates a main queue and a DLQ with 14-day retention.
    
    Args:
        kms_key: KMS key for encryption
        tags: Tags to apply
        
    Returns:
        Dictionary with 'main_queue' and 'dlq' queue references
    """
    
    # Create DLQ first (14 days retention)
    dlq = aws.sqs.Queue(
        "content-tagger-dlq",
        name="content-tagger-dlq",
        message_retention_seconds=14 * 24 * 60 * 60,  # 14 days
        kms_master_key_id=kms_key.id,
        kms_data_key_reuse_period_seconds=300,
        tags={**tags, "Name": "content-tagger-dlq"},
    )
    
    # Create main queue with DLQ configured
    main_queue = aws.sqs.Queue(
        "content-tagger-queue",
        name="content-tagger-queue",
        visibility_timeout_seconds=360,  # 6x Lambda timeout (60s)
        message_retention_seconds=4 * 24 * 60 * 60,  # 4 days
        kms_master_key_id=kms_key.id,
        kms_data_key_reuse_period_seconds=300,
        redrive_policy=dlq.arn.apply(
            lambda dlq_arn: pulumi.Output.json_dumps({
                "deadLetterTargetArn": dlq_arn,
                "maxReceiveCount": 3
            })
        ),
        tags={**tags, "Name": "content-tagger-queue"},
    )
    
    return {
        "main_queue": main_queue,
        "dlq": dlq
    }


def create_content_tagger_eventbridge_rules(
    bucket: aws.s3.Bucket,
    sqs_queue: aws.sqs.Queue,
    tags: Dict[str, str]
) -> Dict[str, aws.cloudwatch.EventRule]:
    """
    Create EventBridge rule to trigger SQS queue for .json files.
    
    Triggers on:
    - Meta files (.meta.json)
    - Config files (config/content-tagging/*.json)
    
    Args:
        bucket: S3 bucket
        sqs_queue: SQS queue to send events to
        tags: Tags to apply
        
    Returns:
        Dictionary of EventBridge rules
    """
    # Simplified rule to match ANY .json file
    json_files_rule = aws.cloudwatch.EventRule(
        "json-files-rule",
        description="Trigger SQS for any .json file (create/update)",
        event_pattern=bucket.id.apply(
            lambda bucket_name: pulumi.Output.json_dumps({
                "source": ["aws.s3"],
                "detail-type": ["Object Created"],
                "detail": {
                    "bucket": {
                        "name": [bucket_name]
                    },
                    "object": {
                        "key": [{"suffix": ".json"}]
                    }
                }
            })
        ),
        tags={**tags, "Name": "json-files-rule"},
    )
    
    # Allow EventBridge to send messages to SQS - must be created before EventTarget
    queue_policy = aws.sqs.QueuePolicy(
        "content-tagger-queue-policy",
        queue_url=sqs_queue.url,
        policy=pulumi.Output.all(
            sqs_queue.arn,
            json_files_rule.arn
        ).apply(
            lambda args: pulumi.Output.json_dumps({
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "AllowEventBridgeToSendMessage",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "events.amazonaws.com"
                        },
                        "Action": "sqs:SendMessage",
                        "Resource": args[0],
                        "Condition": {
                            "ArnEquals": {
                                "aws:SourceArn": args[1]
                            }
                        }
                    }
                ]
            })
        ),
    )
    
    # Target SQS queue - depends on queue policy being in place
    aws.cloudwatch.EventTarget(
        "json-files-sqs-target",
        rule=json_files_rule.name,
        arn=sqs_queue.arn,
        opts=pulumi.ResourceOptions(depends_on=[queue_policy]),
    )
    
    return {"json_files": json_files_rule}


def create_content_tagger_iam_role(
    knowledge_base_bucket: aws.s3.Bucket,
    kms_key: aws.kms.Key,
    sqs_queue: aws.sqs.Queue,
    dlq: aws.sqs.Queue,
    tags: Dict[str, str]
) -> tuple[aws.iam.Role, list]:
    """
    Create IAM role for content tagger Lambda with necessary permissions.
    
    Args:
        knowledge_base_bucket: Knowledge base S3 bucket
        kms_key: KMS key for encryption/decryption
        sqs_queue: Main SQS queue
        dlq: Dead letter queue
        tags: Tags to apply
        
    Returns:
        Tuple of (IAM role, list of policy attachments) - use attachments in depends_on
    """
    
    role = aws.iam.Role(
        "content-tagger-role",
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
        tags={**tags, "Name": "content-tagger-role"},
    )
    
    # Store policy attachments to ensure they're applied before Lambda creation
    policy_attachments = []
    
    basic_exec = aws.iam.RolePolicyAttachment(
        "content-tagger-basic-execution",
        role=role.name,
        policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    )
    policy_attachments.append(basic_exec)
    
    xray = aws.iam.RolePolicyAttachment(
        "content-tagger-xray",
        role=role.name,
        policy_arn="arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess",
    )
    policy_attachments.append(xray)
    
    policy = aws.iam.Policy(
        "content-tagger-policy",
        description="Policy for Content Tagger Lambda function",
        policy=pulumi.Output.all(
            knowledge_base_bucket.arn,
            kms_key.arn,
            sqs_queue.arn,
            dlq.arn
        ).apply(
            lambda args: f"""{{
                "Version": "2012-10-17",
                "Statement": [
                    {{
                        "Sid": "QConnectAccess",
                        "Effect": "Allow",
                        "Action": [
                            "qconnect:GetContent",
                            "qconnect:SearchContent",
                            "qconnect:TagResource",
                            "qconnect:ListContents",
                            "wisdom:GetContent",
                            "wisdom:SearchContent",
                            "wisdom:TagResource",
                            "wisdom:ListContents"
                        ],
                        "Resource": "*"
                    }},
                    {{
                        "Sid": "S3ReadAccess",
                        "Effect": "Allow",
                        "Action": [
                            "s3:GetObject",
                            "s3:ListBucket"
                        ],
                        "Resource": [
                            "{args[0]}",
                            "{args[0]}/*"
                        ]
                    }},
                    {{
                        "Sid": "KMSDecryptAccess",
                        "Effect": "Allow",
                        "Action": [
                            "kms:Decrypt",
                            "kms:DescribeKey"
                        ],
                        "Resource": "{args[1]}"
                    }},
                    {{
                        "Sid": "SQSAccess",
                        "Effect": "Allow",
                        "Action": [
                            "sqs:ReceiveMessage",
                            "sqs:DeleteMessage",
                            "sqs:GetQueueAttributes"
                        ],
                        "Resource": [
                            "{args[2]}",
                            "{args[3]}"
                        ]
                    }}
                ]
            }}"""
        ),
        tags=tags,
    )
    
    custom_policy = aws.iam.RolePolicyAttachment(
        "content-tagger-custom-policy",
        role=role.name,
        policy_arn=policy.arn,
    )
    policy_attachments.append(custom_policy)
    
    return role, policy_attachments


def create_qconnect_knowledge_bucket(tags: Dict[str, str], kms_key: aws.kms.Key, logging_bucket: aws.s3.Bucket) -> aws.s3.Bucket:
    """
    Create S3 bucket for QConnect knowledge base content and configuration.
    
    Args:
        tags: Tags to apply to the bucket
        kms_key: KMS key for encryption
        logging_bucket: S3 bucket to store access logs
        
    Returns:
        S3 bucket for knowledge base content and configuration
    """
    
    bucket = aws.s3.Bucket(
        "q-knowledge-bucket",
        object_lock_enabled=True,
        tags={**tags, "Purpose": "QConnectKnowledgeBase"},
    )
    
    aws.s3.BucketVersioning(
        "q-knowledge-bucket-versioning",
        bucket=bucket.id,
        versioning_configuration=aws.s3.BucketVersioningVersioningConfigurationArgs(
            status="Enabled",
        ),
    )
    
    aws.s3.BucketServerSideEncryptionConfiguration(
        "q-knowledge-bucket-encryption",
        bucket=bucket.id,
        rules=[
            aws.s3.BucketServerSideEncryptionConfigurationRuleArgs(
                apply_server_side_encryption_by_default=aws.s3.BucketServerSideEncryptionConfigurationRuleApplyServerSideEncryptionByDefaultArgs(
                    sse_algorithm="aws:kms",
                    kms_master_key_id=kms_key.arn,
                ),
                bucket_key_enabled=True,
            )
        ],
    )
    
    aws.s3.BucketPublicAccessBlock(
        "q-knowledge-bucket-public-access-block",
        bucket=bucket.id,
        block_public_acls=True,
        block_public_policy=True,
        ignore_public_acls=True,
        restrict_public_buckets=True,
    )
    
    aws.s3.BucketLifecycleConfiguration(
        "q-knowledge-bucket-lifecycle",
        bucket=bucket.id,
        rules=[
            aws.s3.BucketLifecycleConfigurationRuleArgs(
                id="delete-old-versions",
                status="Enabled",
                noncurrent_version_expiration=aws.s3.BucketLifecycleConfigurationRuleNoncurrentVersionExpirationArgs(
                    noncurrent_days=90,
                ),
            )
        ],
    )
    
    # Enable server access logging
    aws.s3.BucketLogging(
        "q-knowledge-bucket-logging",
        bucket=bucket.id,
        target_bucket=logging_bucket.id,
        target_prefix="q-knowledge-bucket/",
    )
    
    return bucket


__all__ = [
    "create_qconnect_integration",
    "create_qconnect_knowledge_bucket",
]