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
Content Tagger Lambda Function

Automatically tags Amazon Q Connect content based on:
1. Folder-based tagging rules (s3.json)
2. Per-document meta files (.meta.json)

Triggers via:
- EventBridge S3 events → SQS → Lambda (batch processing)
- Supports partial batch failures (batchItemFailures)
- 30-second batch window for efficient processing
"""

import json
import os
from typing import Dict, Any, List
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from services import QConnectService, S3Service, TaggingService

# Initialize PowerTools with sensible defaults
logger = Logger(
    service=os.getenv('POWERTOOLS_SERVICE_NAME', 'content-tagger'),
    level=os.getenv('LOG_LEVEL', 'INFO')
)

tracer = Tracer(
    service=os.getenv('POWERTOOLS_SERVICE_NAME', 'content-tagger')
)

metrics = Metrics(
    namespace=os.getenv('POWERTOOLS_METRICS_NAMESPACE', 'AmazonConnect'),
    service=os.getenv('POWERTOOLS_SERVICE_NAME', 'content-tagger')
)

# Environment variables
KNOWLEDGE_BASE_ID = os.getenv('KNOWLEDGE_BASE_ID')
CONFIG_BUCKET = os.getenv('CONFIG_BUCKET')
CONFIG_KEY = os.getenv('CONFIG_KEY', 'config/content-tagging/s3.json')


@tracer.capture_lambda_handler
@logger.inject_lambda_context
@metrics.log_metrics
def handler(event, context):
    """
    Lambda handler for content tagging from SQS batches.
    
    Processes EventBridge events delivered via SQS with support for
    partial batch failures.
    """
    
    logger.info("=== CONTENT TAGGER INVOCATION ===")
    logger.info("SQS batch received", extra={
        "record_count": len(event.get('Records', [])),
        "function_name": context.function_name,
        "function_version": context.function_version,
        "aws_request_id": context.aws_request_id,
        "remaining_time_ms": context.get_remaining_time_in_millis()
    })
    
    # Add invocation metric
    metrics.add_metric(name="ContentTaggerInvocation", unit=MetricUnit.Count, value=1)
    metrics.add_metric(name="SQSRecordsReceived", unit=MetricUnit.Count, value=len(event.get('Records', [])))
    
    try:
        # Validate environment variables
        if not KNOWLEDGE_BASE_ID:
            raise ValueError("KNOWLEDGE_BASE_ID environment variable is required")
        
        if not CONFIG_BUCKET:
            raise ValueError("CONFIG_BUCKET environment variable is required")
        
        # Initialize services
        qconnect = QConnectService(KNOWLEDGE_BASE_ID)
        s3_service = S3Service()
        
        # Load tagging configuration
        config = s3_service.read_config_file(CONFIG_BUCKET, CONFIG_KEY)
        tagging_service = TaggingService(config)
        
        # Process SQS records and track failures
        batch_item_failures = []
        success_count = 0
        skip_count = 0
        
        for record in event.get('Records', []):
            message_id = record.get('messageId')
            
            try:
                # Parse EventBridge event from SQS message body
                eventbridge_event = json.loads(record.get('body', '{}'))
                
                # Extract S3 event details from EventBridge
                s3_event = extract_s3_event_from_eventbridge(eventbridge_event)
                
                if not s3_event:
                    logger.warning("No S3 event found in EventBridge message", extra={
                        "message_id": message_id
                    })
                    skip_count += 1
                    continue
                
                # Process the S3 event
                result = process_s3_event(
                    s3_event,
                    qconnect,
                    s3_service,
                    tagging_service
                )
                
                if result.get('status') == 'success':
                    success_count += 1
                elif result.get('status') == 'skipped':
                    skip_count += 1
                else:
                    # Consider errors as skipped since they're often transient
                    skip_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing SQS record {message_id}: {str(e)}", exc_info=True)
                metrics.add_metric(name="RecordProcessingError", unit=MetricUnit.Count, value=1)
                
                # Add to batch failures for retry
                batch_item_failures.append({
                    "itemIdentifier": message_id
                })
        
        # Summary
        total_records = len(event.get('Records', []))
        
        logger.info("=== PROCESSING COMPLETE ===")
        logger.info("Summary", extra={
            "total_records": total_records,
            "successful": success_count,
            "skipped": skip_count,
            "failed": len(batch_item_failures),
            "remaining_time_ms": context.get_remaining_time_in_millis()
        })
        
        # Add summary metrics
        metrics.add_metric(name="RecordsProcessed", unit=MetricUnit.Count, value=total_records)
        metrics.add_metric(name="RecordsSuccessful", unit=MetricUnit.Count, value=success_count)
        metrics.add_metric(name="RecordsSkipped", unit=MetricUnit.Count, value=skip_count)
        metrics.add_metric(name="RecordsFailed", unit=MetricUnit.Count, value=len(batch_item_failures))
        
        # Return partial batch failures for Lambda to retry
        return {
            "batchItemFailures": batch_item_failures
        }
        
    except Exception as e:
        logger.error(f"Fatal error in handler: {str(e)}", exc_info=True)
        metrics.add_metric(name="HandlerError", unit=MetricUnit.Count, value=1)
        
        # On fatal error, fail all messages for retry
        return {
            "batchItemFailures": [
                {"itemIdentifier": record.get('messageId')}
                for record in event.get('Records', [])
            ]
        }


def extract_s3_event_from_eventbridge(eventbridge_event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract S3 event details from EventBridge event.
    
    Args:
        eventbridge_event: EventBridge event containing S3 details
        
    Returns:
        Normalized S3 event with 'bucket' and 'object_key' fields, or None
    """
    if not eventbridge_event:
        return None
    
    # Validate this is an EventBridge S3 event
    if eventbridge_event.get('source') != 'aws.s3':
        logger.warning("Not an S3 EventBridge event", extra={
            "source": eventbridge_event.get('source')
        })
        return None
    
    detail = eventbridge_event.get('detail', {})
    bucket_name = detail.get('bucket', {}).get('name')
    object_key = detail.get('object', {}).get('key')
    
    if not bucket_name or not object_key:
        logger.warning("Missing bucket or object key in EventBridge detail", extra={
            "detail": detail
        })
        return None
    
    return {
        'bucket': bucket_name,
        'object_key': object_key,
        'event_name': eventbridge_event.get('detail-type', 'EventBridge'),
        'event_source': 'eventbridge'
    }


@tracer.capture_method
def process_s3_event(
    s3_event: Dict[str, Any],
    qconnect: QConnectService,
    s3_service: S3Service,
    tagging_service: TaggingService
) -> Dict[str, Any]:
    """
    Process a normalized S3 event.
    
    Args:
        s3_event: Normalized S3 event with 'bucket' and 'object_key'
        qconnect: Q Connect service instance
        s3_service: S3 service instance
        tagging_service: Tagging service instance
        
    Returns:
        Dictionary with processing result
    """
    try:
        bucket = s3_event.get('bucket')
        object_key = s3_event.get('object_key')
        event_name = s3_event.get('event_name', 'Unknown')
        
        if not bucket or not object_key:
            logger.warning("Missing bucket or object_key in event", extra=s3_event)
            return {
                'status': 'error',
                'error': 'Missing bucket or object_key'
            }
        
        logger.info(f"Processing S3 event: {event_name}", extra={
            "bucket": bucket,
            "object_key": object_key,
            "event_name": event_name
        })
        
        # Check if this is a config file update
        if is_config_file(object_key):
            return handle_config_update(object_key)
        
        # Check if this is a meta file update
        if is_meta_file(object_key):
            return handle_meta_file_update(
                bucket,
                object_key,
                qconnect,
                s3_service,
                tagging_service
            )
        
        # Otherwise, handle as content file
        return handle_content_file(
            bucket,
            object_key,
            qconnect,
            s3_service,
            tagging_service
        )
        
    except Exception as e:
        logger.error(f"Error in process_s3_event: {str(e)}", exc_info=True)
        raise


def is_config_file(object_key: str) -> bool:
    """Check if object is the config file."""
    return object_key == CONFIG_KEY


def is_meta_file(object_key: str) -> bool:
    """Check if object is a .meta.json file."""
    return object_key.endswith('.meta.json')


@tracer.capture_method
def handle_config_update(object_key: str) -> Dict[str, Any]:
    """
    Handle config file update.
    
    When s3.json is updated, we log it but don't retag everything.
    Users can manually trigger retagging if needed.
    
    Args:
        object_key: Config file key
        
    Returns:
        Result dictionary
    """
    logger.info(f"Config file updated: {object_key}")
    logger.info("Note: Config changes affect new content only. Retag existing content manually if needed.")
    
    metrics.add_metric(name="ConfigFileUpdate", unit=MetricUnit.Count, value=1)
    
    return {
        'status': 'skipped',
        'reason': 'config_file',
        'message': 'Config file updated successfully'
    }


@tracer.capture_method
def handle_meta_file_update(
    bucket: str,
    meta_key: str,
    qconnect: QConnectService,
    s3_service: S3Service,
    tagging_service: TaggingService
) -> Dict[str, Any]:
    """
    Handle .meta.json file update.
    
    When a meta file is updated, find and retag the associated content file.
    
    Args:
        bucket: S3 bucket name
        meta_key: Meta file key (e.g., 'sample.meta.json')
        qconnect: Q Connect service
        s3_service: S3 service
        tagging_service: Tagging service
        
    Returns:
        Result dictionary
    """
    logger.info(f"Meta file updated: {meta_key}")
    
    # Derive base filename from meta key
    # Example: 'sample.meta.json' -> 'sample'
    # Example: 'folder/document.meta.json' -> 'folder/document'
    if not meta_key.endswith('.meta.json'):
        logger.warning(f"Invalid meta file key: {meta_key}")
        return {
            'status': 'error',
            'error': 'Invalid meta file key format'
        }
    
    base_key = meta_key[:-10]  # Remove '.meta.json'
    logger.debug(f"Base key: {base_key}")
    
    # Try common file extensions to find the content file
    content_extensions = ['.pdf', '.docx', '.doc', '.txt', '.html', '.md']
    content = None
    content_key = None
    
    for ext in content_extensions:
        test_key = base_key + ext
        logger.debug(f"Searching for content: {test_key}")
        content = qconnect.get_content_by_name(test_key)
        if content:
            content_key = test_key
            logger.info(f"Found associated content: {test_key}")
            break
    
    if not content:
        logger.warning(f"No content found for meta file: {meta_key}")
        logger.info("Content may not be ingested yet. Will retry when content is uploaded.")
        
        metrics.add_metric(name="MetaFileNoContent", unit=MetricUnit.Count, value=1)
        
        return {
            'status': 'skipped',
            'reason': 'content_not_found',
            'message': f'No content found associated with {meta_key}'
        }
    
    # Read meta file to get tags
    meta_data = s3_service.read_meta_file(bucket, content_key)
    if not meta_data or 'tags' not in meta_data:
        logger.warning(f"No tags found in meta file: {meta_key}")
        metrics.add_metric(name="MetaFileNoTags", unit=MetricUnit.Count, value=1)
        return {
            'status': 'skipped',
            'reason': 'no_tags_in_meta',
            'message': 'Meta file contains no tags'
        }
    
    meta_tags = meta_data.get('tags', {})
    
    # Get folder-based tags
    folder_tags = tagging_service.get_folder_tags(content_key)
    
    # Merge tags (meta tags override folder tags)
    merged_tags = tagging_service.merge_tags(folder_tags, meta_tags)
    
    if not merged_tags:
        logger.info(f"No tags to apply for: {content_key}")
        metrics.add_metric(name="NoTagsToApply", unit=MetricUnit.Count, value=1)
        return {
            'status': 'skipped',
            'reason': 'no_tags',
            'message': 'No tags to apply'
        }
    
    # Apply tags to content
    qconnect.tag_content(content['contentArn'], merged_tags)
    
    logger.info(
        f"Successfully tagged content from meta file: {meta_key}",
        extra={
            "content_id": content['contentId'],
            "content_key": content_key,
            "tag_count": len(merged_tags)
        }
    )
    
    metrics.add_metric(name="MetaFileTagged", unit=MetricUnit.Count, value=1)
    metrics.add_metric(name="TagsApplied", unit=MetricUnit.Count, value=len(merged_tags))
    
    return {
        'status': 'success',
        'content_id': content['contentId'],
        'tags_applied': len(merged_tags)
    }


@tracer.capture_method
def handle_content_file(
    bucket: str,
    object_key: str,
    qconnect: QConnectService,
    s3_service: S3Service,
    tagging_service: TaggingService
) -> Dict[str, Any]:
    """
    Handle content file creation/update.
    
    Args:
        bucket: S3 bucket name
        object_key: Object key
        qconnect: Q Connect service
        s3_service: S3 service
        tagging_service: Tagging service
        
    Returns:
        Result dictionary
    """
    logger.info(f"Processing content file: {object_key}")
    
    # Find content in Q Connect knowledge base
    content = qconnect.get_content_by_name(object_key)
    
    if not content:
        logger.warning(f"Content not found in knowledge base: {object_key}")
        logger.info("Content may not be ingested yet. Will retry on next update.")
        
        metrics.add_metric(name="ContentNotFound", unit=MetricUnit.Count, value=1)
        
        return {
            'status': 'skipped',
            'reason': 'content_not_ingested',
            'message': 'Content not found in knowledge base'
        }
    
    # Get folder-based tags
    folder_tags = tagging_service.get_folder_tags(object_key)
    
    # Get meta file tags
    meta_data = s3_service.read_meta_file(bucket, object_key)
    meta_tags = meta_data.get('tags', {}) if meta_data else None
    
    # Merge tags
    merged_tags = tagging_service.merge_tags(folder_tags, meta_tags)
    
    if not merged_tags:
        logger.info(f"No tags to apply for: {object_key}")
        
        metrics.add_metric(name="NoTagsToApply", unit=MetricUnit.Count, value=1)
        
        return {
            'status': 'skipped',
            'reason': 'no_tags',
            'message': 'No tags matched for this content'
        }
    
    # Apply tags to content
    qconnect.tag_content(content['contentArn'], merged_tags)
    
    logger.info(
        f"Successfully tagged content: {object_key}",
        extra={
            "content_id": content['contentId'],
            "tag_count": len(merged_tags)
        }
    )
    
    metrics.add_metric(name="ContentTagged", unit=MetricUnit.Count, value=1)
    metrics.add_metric(name="TagsApplied", unit=MetricUnit.Count, value=len(merged_tags))
    
    return {
        'status': 'success',
        'content_id': content['contentId'],
        'tags_applied': len(merged_tags)
    }