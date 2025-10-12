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

Naming Convention: <stage>-sqs-<purpose>[-dlq]-<hash>
Example: dev-sqs-knowledge-tagging-abc123f
Resource Type: sqs (80 char limit)
"""

from typing import Dict, Optional
import pulumi
import pulumi_aws as aws

from .naming import create_name, create_logical_name


def create_sqs_queue(
    purpose: str,
    tags: Dict[str, str],
    kms_key: aws.kms.Key,
    visibility_timeout_seconds: int = 300,
    message_retention_seconds: int = 345600,  # 4 days
    delay_seconds: int = 0,
    redrive_policy: Optional[pulumi.Output[str]] = None,
) -> aws.sqs.Queue:
    """
    Create an SQS queue with encryption and standard configuration.
    
    Naming convention: <stage>-sqs-<purpose>-<hash>
    Example: dev-sqs-knowledge-tagging-abc123f
    
    The logical name includes the stage prefix, and Pulumi automatically
    appends a hash suffix for uniqueness.
    
    Args:
        purpose: Descriptive purpose (e.g., 'knowledge-tagging', 'customer-events')
        tags: Tags to apply to the queue
        kms_key: KMS key for encryption
        visibility_timeout_seconds: Visibility timeout (default: 300s / 5min)
        message_retention_seconds: Message retention (default: 345600s / 4 days)
        delay_seconds: Delivery delay (default: 0)
        redrive_policy: Optional DLQ redrive policy
        
    Returns:
        SQS queue resource
    """
    # Include stage in logical name so Pulumi adds hash suffix
    # Logical: dev-sqs-knowledge-tagging
    # Physical: dev-sqs-knowledge-tagging-abc123f (Pulumi adds hash)
    stage = pulumi.get_stack()
    logical_name = f"{stage}-sqs-{purpose}"
    
    queue = aws.sqs.Queue(
        logical_name,
        # NO name parameter - let Pulumi add hash to logical name
        delay_seconds=delay_seconds,
        visibility_timeout_seconds=visibility_timeout_seconds,
        message_retention_seconds=message_retention_seconds,
        kms_master_key_id=kms_key.id,
        kms_data_key_reuse_period_seconds=300,
        redrive_policy=redrive_policy,
        tags={**tags, "Purpose": purpose},
    )
    
    return queue


def create_sqs_queue_with_dlq(
    purpose: str,
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
    
    This creates two queues with Pulumi auto-generated hash suffixes:
    - Main queue: <stage>-sqs-<purpose>-<hash>
    - DLQ: <stage>-sqs-<purpose>-dlq-<hash>
    
    Examples:
    - dev-sqs-knowledge-tagging-abc123f
    - dev-sqs-knowledge-tagging-dlq-abc123f
    
    Args:
        purpose: Descriptive purpose (e.g., 'knowledge-tagging')
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
    # Generate DLQ logical name with stage and suffix
    # Logical: dev-sqs-knowledge-tagging-dlq
    # Physical: dev-sqs-knowledge-tagging-dlq-abc123f (Pulumi adds hash)
    stage = pulumi.get_stack()
    dlq_logical = f"{stage}-sqs-{purpose}-dlq"
    
    # Create DLQ
    dlq = aws.sqs.Queue(
        dlq_logical,
        # NO name parameter - let Pulumi add hash
        message_retention_seconds=dlq_retention_seconds,
        kms_master_key_id=kms_key.id,
        kms_data_key_reuse_period_seconds=300,
        tags={**tags, "Purpose": f"{purpose}-dlq", "Type": "DeadLetterQueue"},
    )
    
    # Create main queue with DLQ redrive policy
    redrive_policy = dlq.arn.apply(
        lambda dlq_arn: pulumi.Output.json_dumps({
            "deadLetterTargetArn": dlq_arn,
            "maxReceiveCount": max_receive_count
        })
    )
    
    main_queue = create_sqs_queue(
        purpose=purpose,
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
