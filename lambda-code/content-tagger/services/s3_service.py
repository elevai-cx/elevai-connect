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
S3 Service

Handles S3 operations including reading meta files.
"""

import boto3
import json
from typing import Dict, Optional
from aws_lambda_powertools import Logger

logger = Logger(child=True)


class S3Service:
    """Service for S3 operations."""
    
    def __init__(self):
        """Initialize S3 service."""
        self.client = boto3.client('s3')
        logger.debug("Initialized S3Service")
    
    def read_meta_file(self, bucket: str, object_key: str) -> Optional[Dict]:
        """
        Read .meta.json file associated with an object.
        
        Meta file is expected to be at: path/to/document.pdf -> path/to/document.meta.json
        
        Args:
            bucket: S3 bucket name
            object_key: Object key (e.g., 'folder/document.pdf')
            
        Returns:
            Dictionary with 'tags' and optional 'metadata', or None if not found
        """
        try:
            # Generate meta file key
            meta_key = self._get_meta_key(object_key)
            
            logger.debug(f"Looking for meta file: s3://{bucket}/{meta_key}")
            
            # Try to read the meta file
            response = self.client.get_object(
                Bucket=bucket,
                Key=meta_key
            )
            
            # Parse JSON
            meta_content = response['Body'].read().decode('utf-8')
            meta_data = json.loads(meta_content)
            
            logger.info(
                f"Found meta file for object",
                extra={"bucket": bucket, "object_key": object_key, "meta_key": meta_key}
            )
            
            # Validate structure
            if not isinstance(meta_data, dict):
                logger.warning(f"Meta file is not a valid JSON object: {meta_key}")
                return None
            
            return meta_data
            
        except self.client.exceptions.NoSuchKey:
            logger.debug(f"No meta file found for: {object_key}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in meta file: {str(e)}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Error reading meta file: {str(e)}", exc_info=True)
            return None
    
    def _get_meta_key(self, object_key: str) -> str:
        """
        Generate meta file key from object key.
        
        Examples:
            'folder/document.pdf' -> 'folder/document.meta.json'
            'document.html' -> 'document.meta.json'
            
        Args:
            object_key: Original object key
            
        Returns:
            Meta file key
        """
        # Split on last dot to get base name
        parts = object_key.rsplit('.', 1)
        if len(parts) == 2:
            # Has extension
            base = parts[0]
        else:
            # No extension
            base = object_key
        
        return f"{base}.meta.json"
    
    def read_config_file(self, bucket: str, key: str = 'config/content-tagging/s3.json') -> Dict:
        """
        Read tagging configuration file from S3.
        
        Args:
            bucket: S3 bucket name
            key: Configuration file key
            
        Returns:
            Configuration dictionary
        """
        try:
            logger.debug(f"Reading config file: s3://{bucket}/{key}")
            
            response = self.client.get_object(
                Bucket=bucket,
                Key=key
            )
            
            config_content = response['Body'].read().decode('utf-8')
            config = json.loads(config_content)
            
            logger.info(f"Loaded configuration with {len(config.get('taggingRules', []))} rules")
            
            return config
            
        except self.client.exceptions.NoSuchKey:
            logger.warning(f"Config file not found: s3://{bucket}/{key}")
            return {'taggingRules': []}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {str(e)}", exc_info=True)
            return {'taggingRules': []}
        except Exception as e:
            logger.error(f"Error reading config file: {str(e)}", exc_info=True)
            raise
