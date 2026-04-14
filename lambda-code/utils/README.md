# Utils Lambda Function

A router-based Lambda function for Amazon Connect that provides utility functions for contact flows.

## Architecture

The Lambda follows a clean router pattern with AWS PowerTools for observability:

```
lambda/utils/
├── index.py                    # Main router
├── handlers/                   # Handler modules
│   ├── __init__.py
│   ├── queue_to_agent_arn.py   # Agent ARN extraction from queue ARN
│   ├── presigned_url.py       # S3 presigned URL generation
│   ├── q_connect_tags.py      # Amazon Q in Connect tag filtering
│   └── timestamp.py           # UTC timestamp generation
└── requirements.txt
```

## Features

- **Router Pattern**: Main `index.py` routes requests to appropriate handlers based on `requestType`
- **AWS PowerTools**: Full observability with structured logging, tracing, and metrics
- **Type Safety**: Type hints throughout for better code quality
- **Error Handling**: Comprehensive error handling with clear error messages
- **Amazon Connect Compatible**: Response keys formatted for easy use in contact flows

## Supported Request Types

### `q_connect_tags` - Amazon Q in Connect Tag-Based Filtering

Dynamically filters Amazon Q in Connect content based on tags to provide contextual knowledge to agents.

#### Usage in Amazon Connect Contact Flow

1. Add an **Invoke AWS Lambda function** block to your contact flow
2. Configure the block:
   - **Function ARN**: Select your utils Lambda function
   - **Parameters**:
     - `requestType`: `q_connect_tags`
     - `tagFilter`: JSON object defining the tag filter (see examples below)

#### Tag Filter Examples

**Simple Equals Filter**:
```json
{
  "tagCondition": {
    "tagKey": "department",
    "tagValue": "sales"
  }
}
```

**OR Filter (Multiple Values)**:
```json
{
  "orConditions": [
    {
      "tagCondition": {
        "tagKey": "product",
        "tagValue": "widget-a"
      }
    },
    {
      "tagCondition": {
        "tagKey": "product",
        "tagValue": "widget-b"
      }
    }
  ]
}
```

**AND Filter (Multiple Tags)**:
```json
{
  "andConditions": [
    {
      "tagCondition": {
        "tagKey": "department",
        "tagValue": "sales"
      }
    },
    {
      "tagCondition": {
        "tagKey": "region",
        "tagValue": "us-east"
      }
    }
  ]
}
```

#### Response Attributes

The Lambda returns these attributes that you can store in your contact flow:

- `status-code`: HTTP status code (200 for success)
- `body`: Success or error message
- `session-arn`: Full ARN of the Q in Connect session
- `assistant-id`: Q in Connect assistant ID
- `session-id`: Q in Connect session ID
- `tag-filter`: The applied tag filter
- `session-info`: Full session information from the update

#### Error Responses

If an error occurs, the response will include:
- `status-code`: 400 (bad request) or 500 (server error)
- `body`: Descriptive error message
- `error`: `true`

### `timestamp` - UTC Timestamp Generation

Returns the current UTC (Zulu) time as an ISO 8601 string and epoch milliseconds. Useful for marking points in a contact flow — e.g. to later trim a WAV recording to exact timestamps.

#### Usage in Amazon Connect Contact Flow

1. Add an **Invoke AWS Lambda function** block
2. Configure:
   - `requestType`: `timestamp`
   - No additional parameters required

#### Response Attributes

- `status-code`: `200`
- `timestamp`: ISO 8601 Zulu string, e.g. `2026-03-28T19:42:02.368Z`
- `timestamp-epoch`: Milliseconds since epoch, e.g. `1743191322368`

---

### `presigned_url` - S3 Presigned URL Generation

Generates presigned S3 URLs for voicemail objects (WAV recordings and JSON transcripts) stored in the vmail bucket. Accepts S3 URIs in the form `s3://bucket-name/key/path`.

#### Usage in Amazon Connect Contact Flow

1. Add an **Invoke AWS Lambda function** block
2. Configure:
   - `requestType`: `presigned_url`
   - `s3Uri`: S3 URI to generate a presigned URL for (required)
   - `expiry`: Optional URL expiry in seconds (default: 3600)

#### Response Attributes

- `status-code`: `200`
- `presignedUrl`: HTTPS presigned URL

---

### `queue_to_agent_arn` - Agent ARN Extraction

Extracts the agent ARN from an agent-queue ARN found in `ContactData.Queue.ARN`. Amazon Connect agent queues use the form `arn:aws:connect:<region>:<account>:instance/<id>/queue/agent/<agent-id>`, but many Connect APIs require the shorter agent ARN `arn:aws:connect:<region>:<account>:instance/<id>/agent/<agent-id>`. This handler performs that conversion.

#### Usage in Amazon Connect Contact Flow

1. Add an **Invoke AWS Lambda function** block
2. Configure:
   - `requestType`: `queue_to_agent_arn`
   - Optionally pass `queueArn` to override the value from `ContactData.Queue.ARN`

#### Response Attributes

- `status-code`: `200`
- `agent-arn`: The converted agent ARN
- `agent-id`: The agent ID extracted from the ARN

#### Error Responses

- `status-code`: `400` — No Queue ARN available, or the ARN is not an agent queue ARN

---

## Adding New Handlers

To add a new handler:

1. Create a new file in `handlers/` (e.g., `handlers/my_feature.py`)
2. Implement a `handle(event, context)` function
3. Add the handler to `handlers/__init__.py`
4. Register it in the `HANDLERS` dict in `index.py`

Example handler structure:

```python
"""
My Feature Handler

Description of what this handler does.
"""

from typing import Dict, Any
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(child=True)
tracer = Tracer()

@tracer.capture_method
def handle(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Handle my feature requests."""
    logger.info("Processing my feature request")
    
    # Extract parameters
    parameters = event.get('Details', {}).get('Parameters', {})
    
    # Your logic here
    
    return {
        'statusCode': 200,
        'body': 'Success',
        # ... additional response data
    }
```

## IAM Permissions

The Lambda function has the following IAM permissions:

- **Amazon Connect**:
  - `connect:DescribeContact` - Retrieve contact information
  - `connect:GetContactAttributes` - Get contact attributes
  - `connect:UpdateContactAttributes` - Update contact attributes
  - `connect:StartContactRecording` - Start call recording
  - `connect:StopContactRecording` - Stop call recording

- **Amazon Q in Connect (Wisdom)**:
  - `wisdom:UpdateSession` - Update Q in Connect session

- **DynamoDB**: Read/write access to project tables
- **S3**: Get/Put object access
- **CloudWatch Logs**: Write logs (via AWSLambdaBasicExecutionRole)

## Environment Variables

The Lambda is configured with the following environment variables:

- `POWERTOOLS_SERVICE_NAME`: Service name for logging (set to function name)
- `POWERTOOLS_METRICS_NAMESPACE`: CloudWatch metrics namespace (`AmazonConnect`)
- `LOG_LEVEL`: Logging level (`DEBUG` for dev, `WARNING` for prod)
- `POWERTOOLS_LOGGER_LOG_EVENT`: Log full events (`true`)
- `POWERTOOLS_LOGGER_SAMPLE_RATE`: Sampling rate for debug logs (`0.1`)
- `POWERTOOLS_TRACE_DISABLED`: Enable X-Ray tracing (`false`)
- `POWERTOOLS_TRACER_CAPTURE_RESPONSE`: Capture response in traces (`true`)
- `POWERTOOLS_TRACER_CAPTURE_ERROR`: Capture errors in traces (`true`)

## Monitoring

### CloudWatch Logs

Structured logs are written to CloudWatch Logs with 7-day retention:
- Log group: `/aws/lambda/utils`
- Includes correlation IDs, request IDs, and context
- Debug logs sampled at 10%

### CloudWatch Metrics

Custom metrics in the `AmazonConnect` namespace:
- `UtilsInvocation`: Total invocations
- `QconnecttagsInvocation`: Q Connect tag filtering requests
- `QconnecttagsInvocationSuccess`: Successful requests
- `QconnecttagsInvocationError`: Failed requests
- `MissingRequestType`: Requests without requestType
- `UnknownRequestType`: Requests with invalid requestType
- `HandlerExecutionError`: Handler execution failures

### X-Ray Tracing

All handler methods are automatically traced with AWS X-Ray, providing:
- End-to-end request flow visualization
- Performance bottleneck identification
- Error and exception tracking

## Testing

### Local Testing

You can test the Lambda locally by creating a test event:

```python
test_event = {
    "Details": {
        "ContactData": {
            "ContactId": "test-contact-123",
            "InstanceARN": "arn:aws:connect:us-east-1:123456789012:instance/test"
        },
        "Parameters": {
            "requestType": "q_connect_tags",
            "tagFilter": {
                "tagCondition": {
                    "tagKey": "department",
                    "tagValue": "sales"
                }
            }
        }
    }
}
```

### Testing in Amazon Connect

1. Create a test contact flow
2. Add the Lambda invoke block with test parameters
3. Use the **Test** feature in the contact flow editor
4. Check CloudWatch Logs for detailed execution logs

## Troubleshooting

### Common Issues

**"Missing required parameter: requestType"**
- Ensure the `requestType` parameter is set in your contact flow block

**"Unknown requestType"**
- Check that the `requestType` value matches a registered handler (e.g., `q_connect_tags`)
- Available types are listed in the error message

**"Q in Connect session not found in contact"**
- Ensure Amazon Q in Connect is enabled for your instance
- Add an **Amazon Q in Connect** block before the Lambda invoke block
- Verify Contact Lens is enabled and the Set recording block is in the flow

**"Invalid tag filter format"**
- Ensure `tagFilter` is valid JSON
- Check the tag filter structure matches AWS documentation

### Debug Mode

To enable verbose logging:
1. Update the `LOG_LEVEL` environment variable to `DEBUG`
2. All request/response details will be logged
3. Remember to set back to `INFO` or `WARNING` for production

## Best Practices

1. **Always set requestType**: Make it clear which handler should process the request
2. **Handle errors gracefully**: Check `status-code` in your contact flow
3. **Use tag filters wisely**: Keep filters simple and specific for best performance
4. **Monitor metrics**: Set up CloudWatch alarms for error rates
5. **Review logs regularly**: Use CloudWatch Insights to analyze patterns
6. **Test thoroughly**: Test all code paths before deploying to production

## References

- [Amazon Q in Connect Documentation](https://docs.aws.amazon.com/connect/latest/adminguide/amazon-q-connect.html)
- [AWS Lambda Powertools Python](https://docs.powertools.aws.dev/lambda/python/)
- [Amazon Connect Contact Flow Blocks](https://docs.aws.amazon.com/connect/latest/adminguide/contact-blocks.html)
