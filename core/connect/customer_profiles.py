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
Amazon Connect Customer Profiles Integration

Handles the creation and configuration of Customer Profiles domain
and integration with Amazon Connect.
"""

from typing import Dict, Optional
import pulumi
import pulumi_aws as aws
from ..post_deployment_tracker import add_manual_step


def create_customer_profiles_integration(
    connect_instance: aws.connect.Instance,
    kms_key: aws.kms.Key,
    tags: Dict[str, str]
) -> Optional[Dict[str, any]]:
    """
    Create Amazon Connect Customer Profiles domain and integration.
    
    Creates:
    - Customer Profiles domain with encryption
    - Optional SQS error reporting queue
    - Integration with Amazon Connect instance
    
    Args:
        connect_instance: The Amazon Connect instance
        kms_key: KMS key for data encryption
        tags: Tags to apply to resources
        
    Returns:
        Dictionary containing Customer Profiles resources, or None if disabled
    """
    config = pulumi.Config("customer-profiles")
    
    # Check if customer profiles is enabled
    if not config.get_bool("enabled"):
        pulumi.log.info("Customer Profiles integration is disabled")
        return None
    
    # Get configuration with defaults
    auto_association_type = config.get("auto-association-type") or "CREATE_LIMITED_PROFILES_AND_AUTO_ASSOCIATE"
    error_queue_enabled = config.get_bool("error-queue") or False
    
    # Validate auto association type
    valid_types = [
        "CREATE_LIMITED_PROFILES_AND_AUTO_ASSOCIATE",
        "AUTO_ASSOCIATE_PROFILES_ONLY",
        "CREATE_INFERRED_PROFILES_ONLY"
    ]
    
    # Map user-friendly names to API values
    type_mapping = {
        "Create limited profiles and auto-associate profiles": "CREATE_LIMITED_PROFILES_AND_AUTO_ASSOCIATE",
        "Auto-associate profiles only": "AUTO_ASSOCIATE_PROFILES_ONLY",
        "Create inferred profiles only": "CREATE_INFERRED_PROFILES_ONLY",
    }
    
    # Convert user-friendly name to API value if needed
    if auto_association_type in type_mapping:
        auto_association_type = type_mapping[auto_association_type]
    
    if auto_association_type not in valid_types:
        raise ValueError(
            f"Invalid auto-association-type: {auto_association_type}. "
            f"Must be one of: {', '.join(valid_types)}"
        )
    
    # Create error reporting queue if enabled
    error_queue = None
    error_queue_arn = None
    if error_queue_enabled:
        error_queue, error_queue_arn = _create_error_queue(kms_key, tags)
    
    # Create Customer Profiles domain
    domain = _create_customer_profiles_domain(kms_key, tags)
    
    # Register manual setup step
    _register_manual_setup_step(auto_association_type, error_queue_enabled)
    
    if error_queue:
        pulumi.export("customer_profiles_error_queue_name", error_queue.name)
        pulumi.export("customer_profiles_error_queue_arn", error_queue.arn)
    
    return {
        "domain": domain,
        "error_queue": error_queue,
        "error_queue_arn": error_queue_arn,
        "auto_association_type": auto_association_type,
        "manual_setup_required": True
    }


def _create_customer_profiles_domain(
    kms_key: aws.kms.Key,
    tags: Dict[str, str]
) -> aws.customerprofiles.Domain:
    """
    Create Customer Profiles domain with encryption.
    
    Args:
        kms_key: KMS key for data encryption
        tags: Tags to apply to the domain
        
    Returns:
        Customer Profiles domain resource
    """
    # Default expiration of 366 days (1 year + 1 day for leap years)
    config = pulumi.Config("customer-profiles")
    default_expiration_days = config.get_int("default-expiration-days") or 366
    
    domain = aws.customerprofiles.Domain(
        "connect-profiles-domain",
        domain_name="connect-profiles-domain",
        default_expiration_days=default_expiration_days,
        tags={**tags, "Name": "connect-profiles-domain"},
        opts=pulumi.ResourceOptions(depends_on=[kms_key])
    )
    
    return domain


def _create_error_queue(
    kms_key: aws.kms.Key,
    tags: Dict[str, str]
) -> tuple[aws.sqs.Queue, pulumi.Output[str]]:
    """
    Create SQS queue for error reporting with 14 days retention.
    
    Args:
        kms_key: KMS key for queue encryption
        tags: Tags to apply to the queue
        
    Returns:
        Tuple of (SQS queue, queue ARN output)
    """
    # Create dead letter queue first
    dlq = aws.sqs.Queue(
        "customer-profiles-error-dlq",
        name="connect-customer-profiles-error-dlq",
        message_retention_seconds=1209600,  # 14 days
        kms_master_key_id=kms_key.id,
        kms_data_key_reuse_period_seconds=300,
        tags={**tags, "Name": "connect-customer-profiles-error-dlq"},
    )
    
    # Create main error queue
    error_queue = aws.sqs.Queue(
        "customer-profiles-error-queue",
        name="connect-customer-profiles-error-queue",
        message_retention_seconds=1209600,  # 14 days
        kms_master_key_id=kms_key.id,
        kms_data_key_reuse_period_seconds=300,
        redrive_policy=dlq.arn.apply(
            lambda arn: pulumi.Output.json_dumps({
                "deadLetterTargetArn": arn,
                "maxReceiveCount": 3
            })
        ),
        tags={**tags, "Name": "connect-customer-profiles-error-queue"},
        opts=pulumi.ResourceOptions(depends_on=[dlq])
    )
    
    # Create queue policy to allow Customer Profiles to send messages
    queue_policy = error_queue.arn.apply(
        lambda queue_arn: aws.iam.get_policy_document(
            statements=[
                aws.iam.GetPolicyDocumentStatementArgs(
                    sid="AllowCustomerProfilesToSendMessages",
                    effect="Allow",
                    principals=[
                        aws.iam.GetPolicyDocumentStatementPrincipalArgs(
                            type="Service",
                            identifiers=["profile.amazonaws.com"],
                        )
                    ],
                    actions=[
                        "sqs:SendMessage",
                    ],
                    resources=[queue_arn],
                )
            ]
        ).json
    )
    
    aws.sqs.QueuePolicy(
        "customer-profiles-error-queue-policy",
        queue_url=error_queue.id,
        policy=queue_policy,
    )
    
    return error_queue, error_queue.arn


def _register_manual_setup_step(
    auto_association_type: str,
    error_queue_enabled: bool
) -> None:
    """
    Register Customer Profiles manual setup step with the tracker.
    
    Args:
        auto_association_type: The configured auto-association type
        error_queue_enabled: Whether error queue is enabled
    """
    details = {
        "Auto-Association Type": auto_association_type,
        "Error Queue Enabled": str(error_queue_enabled)
    }
    
    add_manual_step(
        title="Associate Customer Profiles domain with Connect instance",
        doc_link="docs/POST_DEPLOYMENT_STEPS.md#3-customer-profiles-domain-association",
        details=details
    )
