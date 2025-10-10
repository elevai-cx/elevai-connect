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
Amazon Q in Connect Tag-Based Filtering Handler

Handles tag-based content filtering for Amazon Q in Connect sessions.
This allows dynamic content segmentation based on contact and agent context.
"""

import json
import os
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

# Initialize PowerTools
logger = Logger(child=True)
tracer = Tracer()

# Initialize AWS clients
connect_client = boto3.client('connect')
qconnect_client = boto3.client('qconnect')


@tracer.capture_method
def handle(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Handle Amazon Q in Connect tag-based filtering requests.
    
    This function:
    1. Retrieves the Q in Connect session from the contact
    2. Applies tag filters to segment content
    3. Returns session information to the contact flow
    
    Args:
        event: Lambda event from Amazon Connect containing contact data and tag filter
        context: Lambda context
        
    Returns:
        Response dict with status and session information
    """
    logger.info("Processing Q in Connect tag filtering request")
    
    # Extract contact data and parameters
    contact_data = event.get('Details', {}).get('ContactData', {})
    parameters = event.get('Details', {}).get('Parameters', {})
    
    contact_id = contact_data.get('ContactId')
    instance_arn = contact_data.get('InstanceARN')
    tag_filter_param = parameters.get('tagFilter')
    
    logger.info("Request details", extra={
        "contact_id": contact_id,
        "instance_arn": instance_arn,
        "has_tag_filter": tag_filter_param is not None
    })
    
    # Validate required parameters
    if not contact_id or not instance_arn:
        error_msg = "Missing required contact data (ContactId or InstanceARN)"
        logger.error(error_msg)
        return create_error_response(400, error_msg)
    
    if not tag_filter_param:
        error_msg = "Missing required parameter: tagFilter"
        logger.error(error_msg)
        return create_error_response(400, error_msg)
    
    # Parse tag filter (it may come as a JSON string)
    try:
        tag_filter = parse_tag_filter(tag_filter_param)
        logger.debug("Parsed tag filter", extra={"tag_filter": tag_filter})
    except ValueError as e:
        error_msg = f"Invalid tag filter format: {str(e)}"
        logger.error(error_msg)
        return create_error_response(400, error_msg)
    
    # Step 1: Retrieve Q in Connect session from contact
    try:
        session_info = get_qconnect_session(instance_arn, contact_id)
        logger.info("Retrieved Q in Connect session", extra={
            "session_arn": session_info['session_arn'],
            "assistant_id": session_info['assistant_id'],
            "session_id": session_info['session_id']
        })
    except ClientError as e:
        error_msg = f"Failed to retrieve contact: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return create_error_response(500, error_msg)
    except KeyError as e:
        error_msg = f"Q in Connect session not found in contact: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return create_error_response(404, error_msg)
    
    # Step 2: Update session with tag filter
    try:
        update_response = update_qconnect_session(
            assistant_id=session_info['assistant_id'],
            session_id=session_info['session_id'],
            tag_filter=tag_filter
        )
        
        logger.info("Successfully updated Q in Connect session with tag filter")
        
        return {
            'statusCode': 200,
            'body': f"Success - Updated Q in Connect session with tag filter",
            'sessionArn': session_info['session_arn'],
            'assistantId': session_info['assistant_id'],
            'sessionId': session_info['session_id'],
            'tagFilter': tag_filter,
            'sessionInfo': update_response
        }
        
    except Exception as e:
        error_msg = f"Failed to update Q in Connect session: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return create_error_response(500, error_msg)


@tracer.capture_method
def get_qconnect_session(instance_arn: str, contact_id: str) -> Dict[str, str]:
    """
    Retrieve Q in Connect session information from a contact.
    
    Args:
        instance_arn: Amazon Connect instance ARN
        contact_id: Contact ID
        
    Returns:
        Dict containing session_arn, assistant_id, and session_id
        
    Raises:
        ClientError: If API call fails
        KeyError: If session information is not found
    """
    response = connect_client.describe_contact(
        InstanceId=instance_arn,
        ContactId=contact_id
    )
    
    contact = response.get('Contact', {})
    wisdom_info = contact.get('WisdomInfo', {})
    session_arn = wisdom_info.get('SessionArn')
    
    if not session_arn:
        raise KeyError("WisdomInfo.SessionArn not found in contact")
    
    # Parse session ARN: arn:aws:wisdom:region:account:assistant/assistant-id/session/session-id
    # Split format: ['arn:aws:wisdom:region:account:assistant', 'assistant-id', 'session-id']
    arn_parts = session_arn.split('/')
    if len(arn_parts) < 3:
        raise ValueError(f"Invalid session ARN format: {session_arn}")
    
    return {
        'session_arn': session_arn,
        'assistant_id': arn_parts[1],
        'session_id': arn_parts[2]
    }


@tracer.capture_method
def update_qconnect_session(
    assistant_id: str,
    session_id: str,
    tag_filter: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update Amazon Q in Connect session with tag filter.
    
    Args:
        assistant_id: Q in Connect assistant ID
        session_id: Q in Connect session ID
        tag_filter: Tag filter configuration
        
    Returns:
        Session update response
        
    Raises:
        ClientError: If API call fails
    """
    response = qconnect_client.update_session(
        assistantId=assistant_id,
        sessionId=session_id,
        tagFilter=tag_filter
    )
    
    return response.get('session', {})


def parse_tag_filter(tag_filter_param: Any) -> Dict[str, Any]:
    """
    Parse tag filter parameter which may be a string or dict.
    
    Args:
        tag_filter_param: Tag filter as string (JSON) or dict
        
    Returns:
        Parsed tag filter dict
        
    Raises:
        ValueError: If parsing fails
    """
    if isinstance(tag_filter_param, dict):
        return tag_filter_param
    
    if isinstance(tag_filter_param, str):
        try:
            return json.loads(tag_filter_param)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in tagFilter: {str(e)}")
    
    raise ValueError(f"tagFilter must be a dict or JSON string, got {type(tag_filter_param)}")


def create_error_response(status_code: int, error_message: str) -> Dict[str, Any]:
    """
    Create a standardized error response.
    
    Args:
        status_code: HTTP status code
        error_message: Error message
        
    Returns:
        Error response dict
    """
    return {
        'statusCode': status_code,
        'body': error_message,
        'error': True
    }
