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
Resource Naming Utilities

Provides consistent naming standards across all Pulumi resources.
Format: <stage>-<resourceType>-<descriptive-purpose>

AWS Resource Name Limits:
- S3 Bucket: 63 characters
- lbd Function: 64 characters
- IAM Role: 64 characters
- IAM Policy: 128 characters
- SQS Queue: 80 characters
- Kinesis Data Stream: 128 characters
- Kinesis Video Stream: 256 characters
- Kinesis Firehose: 64 characters
- CloudWatch Log Group: 512 characters

Pulumi Hash:
When Pulumi auto-generates resource names, it appends a random hash (e.g., -a1b2c3d)
This is typically 8 characters including the dash. Set reserve_for_hash=True to 
account for this when validating length.
"""

import pulumi
from typing import Optional


# Pulumi hash format: -a1b2c3d (7 chars + 1 dash = 8 total)
PULUMI_HASH_LENGTH = 8

# AWS resource name length limits
LIMITS = {
    "s3": 63,
    "lbd": 64,  # Alias for lbd
    "iam-role": 64,
    "iam-policy": 128,
    "sqs": 80,
    "kds": 128,  # Kinesis Data Stream
    "kvs": 256,  # Kinesis Video Stream
    "kfs": 64,   # Kinesis Firehose Stream
    "cw": 512,  # Alias for cloudwatch
    "connect": 128,  # Generous default for Connect resources
    "default": 128,  # Default limit if not specified
}


def get_stage() -> str:
    """
    Get the current Pulumi stack name to use as the stage/environment.
    
    Returns:
        Stack name (e.g., 'dev', 'staging', 'prod')
    """
    return pulumi.get_stack()


def create_name(
    resource_type: str,
    purpose: str,
    stage: Optional[str] = None,
    suffix: Optional[str] = None,
    reserve_for_hash: bool = False
) -> str:
    """
    Create a standardized resource name following the pattern:
    <stage>-<resourceType>-<purpose>[-suffix]
    
    Args:
        resource_type: Type of resource (e.g., 'kds', 'lbd', 'sqs', 'kvs', 'kfs', 'iam-role', 'iam-policy')
        purpose: Descriptive purpose (e.g., 'contact-records', 'agent-events')
        stage: Optional stage override (default: current stack)
        suffix: Optional suffix (e.g., 'dlq' for dead letter queue)
        reserve_for_hash: If True, reserves space for Pulumi's auto-generated hash
                         (8 characters: -a1b2c3d) when validating length
        
    Returns:
        Standardized resource name
        
    Raises:
        ValueError: If the generated name exceeds AWS limits for the resource type
        
    Examples:
        >>> create_name('kds', 'contact-records')
        'dev-kds-contact-records'
        
        >>> create_name('sqs', 'customer-profiles-error', suffix='dlq')
        'dev-sqs-customer-profiles-error-dlq'
        
        >>> create_name('iam-policy', 'lbd-execution')
        'dev-iam-policy-lbd-execution'
        
        >>> create_name('s3', 'customer-data', reserve_for_hash=True)
        'dev-s3-customer-data'  # Validated to ensure room for -a1b2c3d
    """
    if not stage:
        stage = get_stage()
    
    # Build the name
    parts = [stage, resource_type, purpose]
    if suffix:
        parts.append(suffix)
    
    name = "-".join(parts)
    
    # Check length limit
    limit = LIMITS.get(resource_type.lower(), LIMITS["default"])
    
    # Reserve space for Pulumi hash if requested
    effective_limit = limit - PULUMI_HASH_LENGTH if reserve_for_hash else limit
    
    if len(name) > effective_limit:
        hash_note = f" (with {PULUMI_HASH_LENGTH} chars reserved for Pulumi hash)" if reserve_for_hash else ""
        raise ValueError(
            f"Generated name '{name}' ({len(name)} chars) exceeds AWS limit "
            f"for {resource_type} ({effective_limit} chars{hash_note}). "
            f"Consider shortening the purpose or using abbreviations."
        )
    
    return name


def create_logical_name(
    resource_type: str,
    purpose: str,
    suffix: Optional[str] = None
) -> str:
    """
    Create a logical name for Pulumi resource registration.
    Does not include stage prefix to keep logical names concise.
    
    Note: The AWS resource names (created with create_name()) will still include
    the stage prefix. This is just for Pulumi's internal tracking.
    
    Format: <resourceType>-<purpose>[-suffix]
    
    Args:
        resource_type: Type of resource (e.g., 'kds', 'lbd', 'sqs', 'kvs', 'kfs', 'iam-role', 'iam-policy')
        purpose: Descriptive purpose
        suffix: Optional suffix
        
    Returns:
        Logical name for Pulumi resource
        
    Examples:
        >>> create_logical_name('kds', 'contact-records')
        'kds-contact-records'
        
        >>> create_logical_name('kvs', 'live-media')
        'kvs-live-media'
    """
    parts = [resource_type, purpose]
    if suffix:
        parts.append(suffix)
    
    return "-".join(parts)


def validate_length(
    name: str, 
    resource_type: str,
    reserve_for_hash: bool = False
) -> bool:
    """
    Validate that a name meets AWS length requirements.
    
    Args:
        name: The resource name to validate
        resource_type: Type of resource for limit lookup
        reserve_for_hash: If True, reserves space for Pulumi's hash
        
    Returns:
        True if valid, False otherwise
    """
    limit = LIMITS.get(resource_type.lower(), LIMITS["default"])
    effective_limit = limit - PULUMI_HASH_LENGTH if reserve_for_hash else limit
    return len(name) <= effective_limit


def get_limit(resource_type: str, reserve_for_hash: bool = False) -> int:
    """
    Get the AWS name length limit for a resource type.
    
    Args:
        resource_type: Type of resource
        reserve_for_hash: If True, subtracts space for Pulumi's hash
        
    Returns:
        Maximum allowed length
    """
    limit = LIMITS.get(resource_type.lower(), LIMITS["default"])
    return limit - PULUMI_HASH_LENGTH if reserve_for_hash else limit


def check_name_fits(
    resource_type: str,
    purpose: str,
    stage: Optional[str] = None,
    suffix: Optional[str] = None,
    reserve_for_hash: bool = False
) -> tuple[bool, str, int, int]:
    """
    Check if a name would fit within AWS limits without creating it.
    Useful for validation before resource creation.
    
    Args:
        resource_type: Type of resource
        purpose: Descriptive purpose
        stage: Optional stage override
        suffix: Optional suffix
        reserve_for_hash: If True, reserves space for Pulumi's hash
        
    Returns:
        Tuple of (fits: bool, name: str, length: int, limit: int)
        
    Example:
        >>> fits, name, length, limit = check_name_fits('sqs', 'very-long-queue-name')
        >>> if not fits:
        ...     print(f"Name '{name}' ({length}) exceeds limit ({limit})")
    """
    if not stage:
        stage = get_stage()
    
    parts = [stage, resource_type, purpose]
    if suffix:
        parts.append(suffix)
    
    name = "-".join(parts)
    limit = get_limit(resource_type, reserve_for_hash)
    length = len(name)
    
    return (length <= limit, name, length, limit)
