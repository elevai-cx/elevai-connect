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
Tagging Service

Implements the hybrid tagging strategy combining folder rulesets and meta files.
"""

from typing import Dict, Optional, List
from aws_lambda_powertools import Logger

logger = Logger(child=True)


class TaggingService:
    """Service for determining and merging tags from multiple sources."""
    
    def __init__(self, tagging_config: Dict):
        """
        Initialize tagging service.
        
        Args:
            tagging_config: Configuration dictionary with 'taggingRules'
        """
        self.tagging_rules = tagging_config.get('taggingRules', [])
        logger.debug(f"Initialized TaggingService with {len(self.tagging_rules)} rules")
    
    def get_folder_tags(self, object_key: str) -> Dict[str, str]:
        """
        Get tags based on folder ruleset matching.
        
        Args:
            object_key: S3 object key
            
        Returns:
            Dictionary of tags from matching rule, or empty dict
        """
        try:
            logger.debug(f"Checking folder rules for: {object_key}")
            
            # Extract folder path from object key
            folder_path = self._get_folder_path(object_key)
            
            # Find matching rule
            for rule in self.tagging_rules:
                if self._rule_matches(rule, object_key, folder_path):
                    tags = rule.get('tags', {})
                    logger.info(
                        f"Matched tagging rule",
                        extra={
                            "object_key": object_key,
                            "folder_name": rule.get('folderName'),
                            "tag_count": len(tags)
                        }
                    )
                    return tags
            
            logger.debug(f"No matching folder rule found for: {object_key}")
            return {}
            
        except Exception as e:
            logger.error(f"Error getting folder tags: {str(e)}", exc_info=True)
            return {}
    
    def merge_tags(
        self,
        folder_tags: Dict[str, str],
        meta_tags: Optional[Dict[str, str]]
    ) -> Dict[str, str]:
        """
        Merge tags from folder rules and meta file.
        
        Meta file tags take precedence over folder tags for duplicate keys.
        
        Args:
            folder_tags: Tags from folder ruleset
            meta_tags: Tags from .meta.json file
            
        Returns:
            Merged dictionary of tags
        """
        merged = {}
        
        # Start with folder tags
        if folder_tags:
            merged.update(folder_tags)
            logger.debug(f"Applied {len(folder_tags)} folder tags")
        
        # Override/add meta tags
        if meta_tags:
            merged.update(meta_tags)
            logger.debug(f"Applied {len(meta_tags)} meta file tags")
        
        if not merged:
            logger.warning("No tags to apply after merging")
        else:
            logger.info(
                f"Merged tags: {len(merged)} total",
                extra={
                    "folder_tag_count": len(folder_tags) if folder_tags else 0,
                    "meta_tag_count": len(meta_tags) if meta_tags else 0,
                    "final_tag_count": len(merged)
                }
            )
        
        # Validate tag limits (AWS limit is 50)
        if len(merged) > 50:
            logger.error(
                f"Tag count exceeds AWS limit of 50: {len(merged)} tags",
                extra={"tag_count": len(merged)}
            )
            raise ValueError(f"Cannot apply {len(merged)} tags (limit: 50)")
        
        return merged
    
    def _get_folder_path(self, object_key: str) -> str:
        """
        Extract folder path from object key.
        
        Args:
            object_key: S3 object key
            
        Returns:
            Folder path (empty string if file is in root)
        """
        parts = object_key.split('/')
        if len(parts) > 1:
            # Join all parts except the filename
            return '/'.join(parts[:-1])
        return ''
    
    def _rule_matches(
        self,
        rule: Dict,
        object_key: str,
        folder_path: str
    ) -> bool:
        """
        Check if a tagging rule matches the object.
        
        A rule matches if:
        1. Object key starts with the folder name, OR
        2. Folder path exactly matches the folder name
        
        Args:
            rule: Tagging rule dictionary
            object_key: S3 object key
            folder_path: Extracted folder path
            
        Returns:
            True if rule matches, False otherwise
        """
        folder_name = rule.get('folderName', '')
        
        # Match if object key starts with folder name
        if object_key.startswith(f"{folder_name}/"):
            return True
        
        # Match if folder path exactly matches
        if folder_path == folder_name:
            return True
        
        return False
