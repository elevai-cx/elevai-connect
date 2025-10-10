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
Amazon Q Connect Service

Handles interactions with Amazon Q Connect (Wisdom) API.
"""

import boto3
from typing import Dict, Optional, List
from aws_lambda_powertools import Logger

logger = Logger(child=True)


class QConnectService:
    """Service for Amazon Q Connect operations."""
    
    def __init__(self, knowledge_base_id: str):
        """
        Initialize Q Connect service.
        
        Args:
            knowledge_base_id: The knowledge base ID
        """
        self.client = boto3.client('qconnect')
        self.knowledge_base_id = knowledge_base_id
        self._content_cache = None  # Cache for list_contents results
        self._cache_built = False
        logger.debug(f"Initialized QConnectService for KB: {knowledge_base_id}")
    
    def _build_content_cache(self) -> Dict[str, Dict]:
        """
        Build a cache of all content indexed by S3 object key.
        
        This cache is built once per Lambda invocation and reused for all files
        in the batch, avoiding repeated API calls.
        
        Returns:
            Dictionary mapping S3 object keys to content summaries
        """
        if self._cache_built:
            return self._content_cache
        
        logger.debug("Building content cache from list_contents")
        cache = {}
        
        response = self.client.list_contents(
            knowledgeBaseId=self.knowledge_base_id,
            maxResults=100
        )
        
        # Add all content to cache
        for summary in response.get('contentSummaries', []):
            metadata = summary.get('metadata', {})
            s3_key = metadata.get('s3.object.key')
            if s3_key:
                cache[s3_key] = summary
        
        # Handle pagination
        next_token = response.get('nextToken')
        page_count = 1
        while next_token:
            page_count += 1
            logger.debug(f"Fetching content page {page_count}")
            response = self.client.list_contents(
                knowledgeBaseId=self.knowledge_base_id,
                maxResults=100,
                nextToken=next_token
            )
            
            for summary in response.get('contentSummaries', []):
                metadata = summary.get('metadata', {})
                s3_key = metadata.get('s3.object.key')
                if s3_key:
                    cache[s3_key] = summary
            
            next_token = response.get('nextToken')
        
        logger.info(f"Built content cache with {len(cache)} items from {page_count} page(s)")
        self._content_cache = cache
        self._cache_built = True
        return cache
    
    def get_content_by_name(self, object_key: str) -> Optional[Dict]:
        """
        Find content in knowledge base by S3 object key.
        
        Amazon Q Connect stores the S3 object key in metadata['s3.object.key'].
        This function uses a cache to avoid repeated API calls when processing batches.
        
        Args:
            object_key: Full S3 object key (e.g., 'sales/emea/file.pdf')
            
        Returns:
            Content data if found, None otherwise
        """
        try:
            logger.debug(f"Searching for content with S3 object key: {object_key}")
            
            # Build/get cache of all content
            cache = self._build_content_cache()
            
            # Look up by S3 key
            summary = cache.get(object_key)
            
            if summary:
                logger.info(f"Found content by S3 key: {summary['contentId']} for object: {object_key}")
                return {
                    'contentId': summary['contentId'],
                    'contentArn': summary['contentArn'],
                    'name': summary['name'],
                    'title': summary.get('title', ''),
                    'status': summary['status']
                }
            
            logger.warning(f"No content found for S3 key: {object_key}")
            return None
            
        except Exception as e:
            logger.error(f"Error searching for content: {str(e)}", exc_info=True)
            raise
    
    def tag_content(self, content_arn: str, tags: Dict[str, str]) -> None:
        """
        Apply tags to content.
        
        Args:
            content_arn: ARN of the content to tag
            tags: Dictionary of tags to apply
        """
        try:
            if not tags:
                logger.warning(f"No tags to apply for content: {content_arn}")
                return
            
            logger.info(
                f"Applying {len(tags)} tags to content",
                extra={"content_arn": content_arn, "tag_count": len(tags)}
            )
            
            self.client.tag_resource(
                resourceArn=content_arn,
                tags=tags
            )
            
            logger.info(
                f"Successfully tagged content: {content_arn}",
                extra={"tags": tags}
            )
            
        except Exception as e:
            logger.error(
                f"Error tagging content: {str(e)}",
                extra={"content_arn": content_arn, "tags": tags},
                exc_info=True
            )
            raise
