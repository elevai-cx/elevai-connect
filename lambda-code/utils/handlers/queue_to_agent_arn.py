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
Queue to Agent ARN Handler

Extracts the agent ARN from an agent-queue ARN found in ContactData.Queue.ARN.

Amazon Connect agent queues have ARNs in the form:
    arn:aws:connect:<region>:<account>:instance/<id>/queue/agent/<agent-id>

Many Connect APIs require the agent ARN in the shorter form:
    arn:aws:connect:<region>:<account>:instance/<id>/agent/<agent-id>

This handler performs that conversion and returns the agent ARN.
"""

import re
from typing import Dict, Any
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(child=True)
tracer = Tracer()

# Matches agent queue ARNs and captures the parts we need
AGENT_QUEUE_ARN_PATTERN = re.compile(
    r'^(arn:aws:connect:[^:]+:[^:]+:instance/[^/]+)/queue/agent/(.+)$'
)


@tracer.capture_method
def handle(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Extract the agent ARN from the Queue ARN in ContactData.

    The Queue ARN is read from event.Details.ContactData.Queue.ARN.
    It can optionally be overridden by passing a `queueArn` parameter.

    Returns:
        {
            "statusCode": 200,
            "agent-arn": "arn:aws:connect:eu-west-2:123456789012:instance/<id>/agent/<agent-id>",
            "agent-id": "<agent-id>"
        }
    """
    contact_data = event.get('Details', {}).get('ContactData', {})
    parameters = event.get('Details', {}).get('Parameters', {})

    # Allow explicit override via parameter, otherwise read from Queue
    queue_arn = parameters.get('queueArn') or contact_data.get('Queue', {}).get('ARN', '')

    if not queue_arn:
        logger.warning("No Queue ARN found in ContactData or parameters")
        return {
            'statusCode': 400,
            'body': 'No Queue ARN available in ContactData.Queue.ARN or queueArn parameter',
            'error': True
        }

    match = AGENT_QUEUE_ARN_PATTERN.match(queue_arn)

    if not match:
        logger.warning("Queue ARN is not an agent queue ARN", extra={
            "queue_arn": queue_arn
        })
        return {
            'statusCode': 400,
            'body': f'Queue ARN is not an agent queue ARN: {queue_arn}',
            'error': True
        }

    instance_prefix = match.group(1)
    agent_id = match.group(2)
    agent_arn = f"{instance_prefix}/agent/{agent_id}"

    logger.info("Extracted agent ARN", extra={
        "queue_arn": queue_arn,
        "agent_arn": agent_arn,
        "agent_id": agent_id
    })

    return {
        'statusCode': 200,
        'agent-arn': agent_arn,
        'agent-id': agent_id
    }
