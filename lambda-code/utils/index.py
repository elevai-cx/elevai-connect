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
Utils Lambda Router

Routes Amazon Connect requests to appropriate handler functions based on requestType.
Follows Lambda best practices with AWS PowerTools for observability.
"""

import os
from typing import Dict, Any
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

# Import handlers
from handlers import q_connect_tags, timestamp

# Initialize PowerTools with service name
logger = Logger(
    service=os.getenv('POWERTOOLS_SERVICE_NAME', 'utils-lambda'),
    level=os.getenv('LOG_LEVEL', 'INFO')
)

tracer = Tracer(
    service=os.getenv('POWERTOOLS_SERVICE_NAME', 'utils-lambda')
)

metrics = Metrics(
    namespace=os.getenv('POWERTOOLS_METRICS_NAMESPACE', 'AmazonConnect'),
    service=os.getenv('POWERTOOLS_SERVICE_NAME', 'utils-lambda')
)

# Handler registry - maps requestType to handler function
HANDLERS = {
    'q_connect_tags': q_connect_tags.handle,
    'qconnect_tags': q_connect_tags.handle,  # Alias for flexibility
    'timestamp': timestamp.handle,
}


@tracer.capture_lambda_handler
@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Main Lambda handler that routes requests to appropriate handlers.
    
    Expected event structure from Amazon Connect:
    {
        "Details": {
            "ContactData": {
                "ContactId": "...",
                "InstanceARN": "...",
                ...
            },
            "Parameters": {
                "requestType": "q_connect_tags",
                ...handler-specific parameters...
            }
        }
    }
    
    Args:
        event: Event from Amazon Connect contact flow
        context: Lambda context
        
    Returns:
        Response dict to be consumed by Amazon Connect
    """
    # Log incoming event
    logger.info("Incoming Amazon Connect event", extra={
        "function_name": context.function_name,
        "function_version": context.function_version,
        "aws_request_id": context.aws_request_id,
        "remaining_time_ms": context.get_remaining_time_in_millis()
    })
    
    # Add invocation metric
    metrics.add_metric(name="UtilsInvocation", unit=MetricUnit.Count, value=1)
    
    # Extract contact information
    contact_data = event.get('Details', {}).get('ContactData', {})
    parameters = event.get('Details', {}).get('Parameters', {})
    contact_id = contact_data.get('ContactId', 'unknown')
    
    # Get request type
    request_type = parameters.get('requestType', '').lower()
    
    logger.info("Processing request", extra={
        "request_type": request_type,
        "contact_id": contact_id
    })
    
    # Route to appropriate handler
    if not request_type:
        logger.warning("Missing requestType parameter")
        metrics.add_metric(name="MissingRequestType", unit=MetricUnit.Count, value=1)
        
        response = {
            'statusCode': 400,
            'body': 'Missing required parameter: requestType',
            'error': True
        }
    
    elif request_type not in HANDLERS:
        logger.warning(f"Unknown request type: {request_type}", extra={
            "available_types": list(HANDLERS.keys())
        })
        metrics.add_metric(name="UnknownRequestType", unit=MetricUnit.Count, value=1)
        
        response = {
            'statusCode': 400,
            'body': f'Unknown requestType: {request_type}. Available types: {", ".join(HANDLERS.keys())}',
            'error': True
        }
    
    else:
        # Execute handler
        try:
            handler_func = HANDLERS[request_type]
            logger.info(f"Routing to handler: {handler_func.__module__}.{handler_func.__name__}")
            
            # Add handler-specific metric
            metric_name = f"{request_type.replace('_', '').title()}Invocation"
            metrics.add_metric(name=metric_name, unit=MetricUnit.Count, value=1)
            
            # Call handler
            response = handler_func(event, context)
            
            # Check if handler succeeded
            if response.get('statusCode') == 200:
                metrics.add_metric(name=f"{metric_name}Success", unit=MetricUnit.Count, value=1)
            else:
                metrics.add_metric(name=f"{metric_name}Error", unit=MetricUnit.Count, value=1)
            
        except Exception as e:
            logger.exception("Handler execution failed", extra={
                "request_type": request_type,
                "error": str(e)
            })
            metrics.add_metric(name="HandlerExecutionError", unit=MetricUnit.Count, value=1)
            
            response = {
                'statusCode': 500,
                'body': f'Internal error: {str(e)}',
                'error': True
            }
    
    # Log outgoing response
    logger.info("Response to Amazon Connect", extra={
        "response": response,
        "contact_id": contact_id,
        "success": response.get('statusCode') == 200,
        "remaining_time_ms": context.get_remaining_time_in_millis()
    })
    
    # Convert response keys to use hyphens for Amazon Connect compatibility
    # Amazon Connect contact flows prefer hyphenated keys for attribute setting
    return normalize_response_keys(response)


def normalize_response_keys(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize response keys for Amazon Connect compatibility.
    
    Amazon Connect contact flows work better with hyphenated keys.
    This converts camelCase to hyphen-case for top-level keys.
    
    Args:
        response: Response dictionary
        
    Returns:
        Response with normalized keys
    """
    normalized = {}
    
    # Map common keys to Connect-friendly format
    key_mapping = {
        'statusCode': 'status-code',
        'sessionArn': 'session-arn',
        'assistantId': 'assistant-id',
        'sessionId': 'session-id',
        'tagFilter': 'tag-filter',
        'sessionInfo': 'session-info'
    }
    
    for key, value in response.items():
        # Use mapping if available, otherwise keep original
        new_key = key_mapping.get(key, key)
        normalized[new_key] = value
    
    return normalized
