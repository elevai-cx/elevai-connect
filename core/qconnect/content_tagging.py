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
Amazon Q Content Tagging

Handles automatic tagging of knowledge base content using Lambda, SQS, and EventBridge.

Naming Convention:
- SQS: <stage>-sqs-<purpose>[-dlq]
- Lambda: <stage>-lambda-<purpose>
- IAM Role: <stage>-iam-role-<purpose>
"""

from typing import Dict, List
import json
import pulumi
import pulumi_aws as aws
import pulumi_aws_native as aws_native

from core.utils import create_sqs_queue_with_dlq, create_lambda_with_requirements, create_lambda_role


def create_content_tagging_infrastructure(
    knowledge_base: aws_native.wisdom.KnowledgeBase,
    bucket: aws.s3.Bucket,
    kms_key: aws.kms.Key,
    tags: Dict[str, str],
    tagging_rules: List[Dict]
) -> Dict:
    """
    Create complete content tagging infrastructure.
    
    This creates:
    - SQS queue with DLQ and 30s delay
    - Lambda function for tagging
    - EventBridge rules for supported file types
    - S3 configuration upload
    
    Args:
        knowledge_base: Knowledge base resource
        bucket: S3 bucket
        kms_key: KMS key
        tags: Tags to apply
        tagging_rules: Content tagging rules from config
        
    Returns:
        Dictionary of created resources
    """
    # Enable EventBridge notifications
    aws.s3.BucketNotification(
        "q-knowledge-bucket-eventbridge",
        bucket=bucket.id,
        eventbridge=True,
    )
    
    # Create SQS queues with 30s delay
    # Physical names: dev-sqs-knowledge-tagging, dev-sqs-knowledge-tagging-dlq
    sqs_queues = create_sqs_queue_with_dlq(
        purpose="knowledge-tagging",
        tags=tags,
        kms_key=kms_key,
        visibility_timeout_seconds=360,  # 6x Lambda timeout
        delay_seconds=30,  # Prevent race conditions
        dlq_retention_seconds=14 * 24 * 60 * 60,  # 14 days
    )
    
    # Create IAM role for Lambda
    # Physical names: dev-iam-role-knowledge-tagging, dev-iam-policy-knowledge-tagging
    policy_statements = _build_lambda_policy_statements(
        bucket, kms_key, sqs_queues
    )
    
    lambda_role, policy_attachments = create_lambda_role(
        purpose="knowledge-tagging",
        tags=tags,
        additional_policy_statements=policy_statements,
    )
    
    # Upload tagging configuration
    tagging_config = {
        "taggingRules": tagging_rules
    }
    
    config_object = aws.s3.BucketObjectv2(
        "q-tagging-config",
        bucket=bucket.id,
        key="config/content-tagging/s3.json",
        content=json.dumps(tagging_config, indent=2),
        content_type="application/json",
        tags={**tags, "Purpose": "ContentTaggingConfig"},
    )
    
    # Create Lambda function
    # Physical name: dev-lbd-knowledge-tagging
    lambda_function = create_lambda_with_requirements(
        purpose="knowledge-tagging",
        lambda_dir="./lambda-code/content-tagger",
        iam_role=lambda_role,
        tags=tags,
        memory_size=512,
        timeout=60,
        environment_variables={
            "KNOWLEDGE_BASE_ID": knowledge_base.knowledge_base_id,
            "CONFIG_BUCKET": bucket.id,
            "CONFIG_KEY": "config/content-tagging/s3.json",
        },
        opts=pulumi.ResourceOptions(depends_on=policy_attachments),
    )
    
    # Configure Lambda to process SQS with batching
    event_source_mapping = aws.lambda_.EventSourceMapping(
        "q-knowledge-tagging-sqs-trigger",
        event_source_arn=sqs_queues["main_queue"].arn,
        function_name=lambda_function.name,
        batch_size=10,
        maximum_batching_window_in_seconds=30,
        function_response_types=["ReportBatchItemFailures"],
        opts=pulumi.ResourceOptions(depends_on=[lambda_function]),
    )
    
    # Create EventBridge rules
    eventbridge_rules = create_eventbridge_rules(
        bucket, sqs_queues["main_queue"], tags
    )
    
    return {
        "lambda_function": lambda_function,
        "sqs_queue": sqs_queues["main_queue"],
        "dlq": sqs_queues["dlq"],
        "event_source_mapping": event_source_mapping,
        "eventbridge_rules": eventbridge_rules,
        "tagging_config": config_object,
    }


def _build_lambda_policy_statements(
    bucket: aws.s3.Bucket,
    kms_key: aws.kms.Key,
    sqs_queues: Dict[str, aws.sqs.Queue]
) -> pulumi.Output[List[Dict]]:
    """Build IAM policy statements for Lambda as a Pulumi Output."""
    return pulumi.Output.all(
        bucket_arn=bucket.arn,
        kms_arn=kms_key.arn,
        queue_arn=sqs_queues["main_queue"].arn,
        dlq_arn=sqs_queues["dlq"].arn
    ).apply(lambda args: [
        {
            "Sid": "QConnectAccess",
            "Effect": "Allow",
            "Action": [
                "wisdom:GetContent",
                "wisdom:SearchContent",
                "wisdom:TagResource",
                "wisdom:ListContents"
            ],
            "Resource": "*"
        },
        {
            "Sid": "S3ReadAccess",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                args["bucket_arn"],
                f"{args['bucket_arn']}/*"
            ]
        },
        {
            "Sid": "KMSDecryptAccess",
            "Effect": "Allow",
            "Action": [
                "kms:Decrypt",
                "kms:DescribeKey"
            ],
            "Resource": args["kms_arn"]
        },
        {
            "Sid": "SQSAccess",
            "Effect": "Allow",
            "Action": [
                "sqs:ReceiveMessage",
                "sqs:DeleteMessage",
                "sqs:GetQueueAttributes"
            ],
            "Resource": [
                args["queue_arn"],
                args["dlq_arn"]
            ]
        }
    ])


def create_eventbridge_rules(
    bucket: aws.s3.Bucket,
    sqs_queue: aws.sqs.Queue,
    tags: Dict[str, str]
) -> Dict[str, aws.cloudwatch.EventRule]:
    """
    Create EventBridge rules for supported Q file types.
    
    Triggers on .html, .docx, .pdf, .txt files only (not .meta.json).
    
    Args:
        bucket: S3 bucket
        sqs_queue: SQS queue
        tags: Tags to apply
        
    Returns:
        Dictionary of EventBridge rules
    """
    supported_extensions = [".html", ".docx", ".pdf", ".txt"]
    
    rule = aws.cloudwatch.EventRule(
        "q-knowledge-supported-files",
        description="Trigger SQS for Amazon Q document file types only",
        event_pattern=bucket.id.apply(
            lambda bucket_name: pulumi.Output.json_dumps({
                "source": ["aws.s3"],
                "detail-type": ["Object Created"],
                "detail": {
                    "bucket": {"name": [bucket_name]},
                    "object": {
                        "key": [
                            {"suffix": ext} for ext in supported_extensions
                        ]
                    }
                }
            })
        ),
        tags={**tags, "Name": "q-knowledge-supported-files"},
    )
    
    # Allow EventBridge to send to SQS
    queue_policy = aws.sqs.QueuePolicy(
        "q-knowledge-tagging-queue-policy",
        queue_url=sqs_queue.url,
        policy=pulumi.Output.all(
            sqs_queue.arn,
            rule.arn
        ).apply(
            lambda args: pulumi.Output.json_dumps({
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "AllowEventBridgeToSendMessage",
                        "Effect": "Allow",
                        "Principal": {"Service": "events.amazonaws.com"},
                        "Action": "sqs:SendMessage",
                        "Resource": args[0],
                        "Condition": {
                            "ArnEquals": {"aws:SourceArn": args[1]}
                        }
                    }
                ]
            })
        ),
    )
    
    # Create EventTarget (depends on queue policy)
    aws.cloudwatch.EventTarget(
        "supported-files-sqs-target",
        rule=rule.name,
        arn=sqs_queue.arn,
        opts=pulumi.ResourceOptions(depends_on=[queue_policy]),
    )
    
    return {"supported_files": rule}
