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
SQS Utilities

Reusable SQS queue creation functions.
"""

from typing import Dict, Optional
import pulumi
import pulumi_aws as aws


def create_sqs_queue(
    resource_name: str,
    queue_name: str,
    tags: Dict[str, str],
    kms_key: aws.kms.Key,
    visibility_timeout_seconds: int = 300,
    message_retention_seconds: int = 345600,  # 4 days
    delay_seconds: int = 0,
    redrive_policy: Optional[pulumi.Output[str]] = None,
) -> aws.sqs.Queue:
    """
    Create an SQS queue with encryption and standard configuration.
    
    Args:
        resource_name: Pulumi resource name
        queue_name: Name for the SQS queue
        tags: Tags to apply to the queue
        kms_key: KMS key for encryption
        visibility_timeout_seconds: Visibility timeout (default: 300s / 5min)
        message_retention_seconds: Message retention (default: 345600s / 4 days)
        delay_seconds: Delivery delay (default: 0)
        redrive_policy: Optional DLQ redrive policy
        
    Returns:
        SQS queue resource
    """
    queue = aws.sqs.Queue(
        resource_name,
        name=queue_name,
        delay_seconds=delay_seconds,
        visibility_timeout_seconds=visibility_timeout_seconds,
        message_retention_seconds=message_retention_seconds,
        kms_master_key_id=kms_key.id,
        kms_data_key_reuse_period_seconds=300,
        redrive_policy=redrive_policy,
        tags={**tags, "Name": queue_name},
    )
    
    return queue


def create_sqs_queue_with_dlq(
    resource_name: str,
    queue_name: str,
    tags: Dict[str, str],
    kms_key: aws.kms.Key,
    visibility_timeout_seconds: int = 300,
    message_retention_seconds: int = 345600,  # 4 days
    dlq_retention_seconds: int = 1209600,  # 14 days
    max_receive_count: int = 3,
    delay_seconds: int = 0,
) -> Dict[str, aws.sqs.Queue]:
    """
    Create an SQS queue with a dead-letter queue (DLQ).
    
    This creates two queues:
    - Main queue with redrive policy
    - DLQ for failed messages
    
    Args:
        resource_name: Base Pulumi resource name
        queue_name: Base name for the queues
        tags: Tags to apply to queues
        kms_key: KMS key for encryption
        visibility_timeout_seconds: Visibility timeout for main queue
        message_retention_seconds: Message retention for main queue
        dlq_retention_seconds: Message retention for DLQ (default: 14 days)
        max_receive_count: Max receives before sending to DLQ (default: 3)
        delay_seconds: Delivery delay for main queue (default: 0)
        
    Returns:
        Dictionary with 'main_queue' and 'dlq' keys
    """
    # Create DLQ first
    dlq = create_sqs_queue(
        resource_name=f"{resource_name}-dlq",
        queue_name=f"{queue_name}-dlq",
        tags={**tags, "Purpose": "DeadLetterQueue"},
        kms_key=kms_key,
        message_retention_seconds=dlq_retention_seconds,
    )
    
    # Create main queue with DLQ redrive policy
    redrive_policy = dlq.arn.apply(
        lambda dlq_arn: pulumi.Output.json_dumps({
            "deadLetterTargetArn": dlq_arn,
            "maxReceiveCount": max_receive_count
        })
    )
    
    main_queue = create_sqs_queue(
        resource_name=resource_name,
        queue_name=queue_name,
        tags=tags,
        kms_key=kms_key,
        visibility_timeout_seconds=visibility_timeout_seconds,
        message_retention_seconds=message_retention_seconds,
        delay_seconds=delay_seconds,
        redrive_policy=redrive_policy,
    )
    
    return {
        "main_queue": main_queue,
        "dlq": dlq
    }
