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
SQS Queues

Creates SQS queues for Amazon Connect event processing and async workflows.
"""

from typing import Dict
import pulumi_aws as aws


def create_sqs_queues(tags: Dict[str, str], kms_key: aws.kms.Key) -> Dict[str, aws.sqs.Queue]:
    """
    Create SQS queues for event processing.
    
    Args:
        tags: Common tags to apply to all queues
        kms_key: KMS key for queue encryption
        
    Returns:
        Dictionary of queue names to SQS queue resources
    """
    queues = {}
    
    # Contact events queue - processes Connect contact events
    contact_events_queue = aws.sqs.Queue(
        "contact-events-queue",
        name="contact-events",
        visibility_timeout_seconds=300,  # 5 minutes
        message_retention_seconds=1209600,  # 14 days
        kms_master_key_id=kms_key.id,
        kms_data_key_reuse_period_seconds=300,
        tags={**tags, "Purpose": "ContactEvents"}
    )
    queues["contact_events"] = contact_events_queue
    
    # Dead letter queue for failed messages
    contact_events_dlq = aws.sqs.Queue(
        "contact-events-dlq",
        name="contact-events-dlq",
        message_retention_seconds=1209600,  # 14 days
        kms_master_key_id=kms_key.id,
        kms_data_key_reuse_period_seconds=300,
        tags={**tags, "Purpose": "ContactEventsDLQ"}
    )
    queues["contact_events_dlq"] = contact_events_dlq
    
    # Configure DLQ redrive policy
    aws.sqs.QueueRedrivePolicy(
        "contact-events-redrive-policy",
        queue_url=contact_events_queue.url,
        redrive_policy=contact_events_dlq.arn.apply(
            lambda arn: f'{{"deadLetterTargetArn":"{arn}","maxReceiveCount":3}}'
        )
    )
    
    return queues
