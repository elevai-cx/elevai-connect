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
        logger.debug(f"Initialized QConnectService for KB: {knowledge_base_id}")
    
    def get_content_by_name(self, object_key: str) -> Optional[Dict]:
        """
        Find content in knowledge base by object key (name).
        
        Searches both by NAME field and S3 object key in metadata.
        
        Args:
            object_key: S3 object key to search for
            
        Returns:
            Content data if found, None otherwise
        """
        try:
            logger.debug(f"Searching for content with object key: {object_key}")
            
            # First try searching by NAME
            response = self.client.search_content(
                knowledgeBaseId=self.knowledge_base_id,
                searchExpression={
                    'filters': [{
                        'field': 'NAME',
                        'operator': 'EQUALS',
                        'value': object_key
                    }]
                }
            )
            
            summaries = response.get('contentSummaries', [])
            
            if summaries:
                content_id = summaries[0]['contentId']
                logger.info(f"Found content by NAME: {content_id} for object: {object_key}")
                return self.get_content_details(content_id)
            
            # If not found by NAME, search all content and match by S3 object key in metadata
            logger.debug(f"Content not found by NAME, searching by S3 object key metadata")
            return self.find_content_by_s3_key(object_key)
            
        except Exception as e:
            logger.error(f"Error searching for content: {str(e)}", exc_info=True)
            raise
    
    def find_content_by_s3_key(self, s3_key: str) -> Optional[Dict]:
        """
        Find content by S3 object key stored in metadata.
        
        Args:
            s3_key: S3 object key (e.g., 'sample.pdf')
            
        Returns:
            Content data if found, None otherwise
        """
        try:
            logger.debug(f"Searching all content for S3 key: {s3_key}")
            
            # List all content and find by metadata
            response = self.client.list_contents(
                knowledgeBaseId=self.knowledge_base_id
            )
            
            for summary in response.get('contentSummaries', []):
                # Check if S3 object key matches in metadata
                metadata = summary.get('metadata', {})
                if metadata.get('s3.object.key') == s3_key:
                    content_id = summary['contentId']
                    logger.info(f"Found content by S3 key: {content_id} for object: {s3_key}")
                    return self.get_content_details(content_id)
            
            logger.debug(f"No content found for S3 key: {s3_key}")
            return None
            
        except Exception as e:
            logger.error(f"Error searching by S3 key: {str(e)}", exc_info=True)
            raise
    
    def get_content_details(self, content_id: str) -> Dict:
        """
        Get detailed information about content.
        
        Args:
            content_id: Content ID
            
        Returns:
            Content details including ARN
        """
        try:
            logger.debug(f"Getting content details for: {content_id}")
            
            response = self.client.get_content(
                knowledgeBaseId=self.knowledge_base_id,
                contentId=content_id
            )
            
            content = response['content']
            logger.debug(f"Retrieved content ARN: {content['contentArn']}")
            
            return {
                'contentId': content['contentId'],
                'contentArn': content['contentArn'],
                'name': content['name'],
                'status': content['status']
            }
            
        except Exception as e:
            logger.error(f"Error getting content details: {str(e)}", exc_info=True)
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
