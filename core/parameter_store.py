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
AWS Systems Manager Parameter Store

Creates Parameter Store items for all key resources to provide a normalized
interface for customers to extend the infrastructure using their IaC of choice.

All parameters use the prefix: /elevai/
"""

from typing import Dict, Any, Optional
import pulumi
import pulumi_aws as aws


def create_parameter_store_items(
    core_resources: Dict[str, Any],
    tags: Dict[str, str]
) -> Dict[str, aws.ssm.Parameter]:
    """
    Create SSM Parameter Store items for all key resources.
    
    This provides a normalized interface for customers to query resource
    information and extend the infrastructure using any IaC tool.
    
    Args:
        core_resources: Dictionary of core infrastructure resources
        tags: Common tags to apply to parameters
        
    Returns:
        Dictionary of parameter names to Parameter resources
    """
    parameters = {}
    prefix = "/elevai"
    
    # Get configuration
    config = pulumi.Config("connect")
    instance_alias = config.get("instanceAlias")
    identity_management_type = config.get("identityManagementType") or "CONNECT_MANAGED"
    
    # Amazon Connect Instance Parameters
    if instance_alias:
        parameters["connect_instance_alias"] = _create_parameter(
            "connect-instance-alias",
            f"{prefix}/connect/instance/alias",
            instance_alias,
            "Amazon Connect instance alias",
            tags
        )
    
    connect_instance = core_resources.get("connect_instance")
    if connect_instance:
        parameters["connect_instance_arn"] = _create_parameter(
            "connect-instance-arn",
            f"{prefix}/connect/instance/arn",
            connect_instance.arn,
            "Amazon Connect instance ARN",
            tags
        )
    
    # S3 Bucket Parameters
    s3_buckets = core_resources.get("s3_buckets", {})
    
    bucket_mappings = {
        "recordings": "call-recordings",
        "chat_transcripts": "chat-transcripts",
        "exported_reports": "exported-reports",
        "attachments": "attachments",
        "screen_recordings": "screen-recordings",
        "contact_evaluations": "contact-evaluations",
        "email_messages": "email-messages"
    }
    
    for bucket_key, param_name in bucket_mappings.items():
        bucket = s3_buckets.get(bucket_key)
        if bucket:
            # Store bucket name
            parameters[f"s3_{bucket_key}_name"] = _create_parameter(
                f"s3-{param_name}-name",
                f"{prefix}/s3/{param_name}/name",
                bucket.id,
                f"S3 bucket name for {param_name}",
                tags
            )
            
            # Store bucket ARN
            parameters[f"s3_{bucket_key}_arn"] = _create_parameter(
                f"s3-{param_name}-arn",
                f"{prefix}/s3/{param_name}/arn",
                bucket.arn,
                f"S3 bucket ARN for {param_name}",
                tags
            )
    
    # QConnect Knowledge Base Bucket (if enabled)
    qconnect_kb_bucket = core_resources.get("qconnect_kb_bucket")
    if qconnect_kb_bucket:
        parameters["s3_qconnect_kb_name"] = _create_parameter(
            "s3-qconnect-kb-name",
            f"{prefix}/s3/qconnect-knowledge-base/name",
            qconnect_kb_bucket.id,
            "S3 bucket name for QConnect knowledge base",
            tags
        )
        
        parameters["s3_qconnect_kb_arn"] = _create_parameter(
            "s3-qconnect-kb-arn",
            f"{prefix}/s3/qconnect-knowledge-base/arn",
            qconnect_kb_bucket.arn,
            "S3 bucket ARN for QConnect knowledge base",
            tags
        )
    
    # Kinesis Data Streams Parameters
    data_streams = core_resources.get("data_streams", {})
    
    # Contact Records Stream
    contact_records_stream = data_streams.get("contact_records")
    if contact_records_stream:
        parameters["kinesis_contact_records_name"] = _create_parameter(
            "kinesis-contact-records-name",
            f"{prefix}/kinesis/stream/contact-records/name",
            contact_records_stream.name,
            "Kinesis stream name for contact records",
            tags
        )
        
        parameters["kinesis_contact_records_arn"] = _create_parameter(
            "kinesis-contact-records-arn",
            f"{prefix}/kinesis/stream/contact-records/arn",
            contact_records_stream.arn,
            "Kinesis stream ARN for contact records",
            tags
        )
    
    # Agent Events Stream
    agent_events_stream = data_streams.get("agent_events")
    if agent_events_stream:
        parameters["kinesis_agent_events_name"] = _create_parameter(
            "kinesis-agent-events-name",
            f"{prefix}/kinesis/stream/agent-events/name",
            agent_events_stream.name,
            "Kinesis stream name for agent events",
            tags
        )
        
        parameters["kinesis_agent_events_arn"] = _create_parameter(
            "kinesis-agent-events-arn",
            f"{prefix}/kinesis/stream/agent-events/arn",
            agent_events_stream.arn,
            "Kinesis stream ARN for agent events",
            tags
        )
    
    # KMS Key Parameters
    kms_key = core_resources.get("kms_key")
    if kms_key:
        parameters["kms_key_id"] = _create_parameter(
            "kms-key-id",
            f"{prefix}/kms/data-encryption-key/id",
            kms_key.id,
            "KMS key ID for data encryption",
            tags
        )
        
        parameters["kms_key_arn"] = _create_parameter(
            "kms-key-arn",
            f"{prefix}/kms/data-encryption-key/arn",
            kms_key.arn,
            "KMS key ARN for data encryption",
            tags
        )
    
    # IAM SAML Identity Provider Parameters (only if using SAML)
    if identity_management_type == "SAML":
        iam_resources = core_resources.get("iam", {})
        
        saml_provider = iam_resources.get("saml_provider")
        if saml_provider:
            parameters["saml_provider_name"] = _create_parameter(
                "saml-provider-name",
                f"{prefix}/iam/saml-provider/name",
                saml_provider.name,
                "SAML identity provider name",
                tags
            )
            
            parameters["saml_provider_arn"] = _create_parameter(
                "saml-provider-arn",
                f"{prefix}/iam/saml-provider/arn",
                saml_provider.arn,
                "SAML identity provider ARN",
                tags
            )
        
        saml_role = iam_resources.get("saml_role")
        if saml_role:
            parameters["saml_role_name"] = _create_parameter(
                "saml-role-name",
                f"{prefix}/iam/saml-role/name",
                saml_role.name,
                "IAM role name for SAML federated access",
                tags
            )
            
            parameters["saml_role_arn"] = _create_parameter(
                "saml-role-arn",
                f"{prefix}/iam/saml-role/arn",
                saml_role.arn,
                "IAM role ARN for SAML federated access",
                tags
            )
    
    # SNS Topic Parameters
    alerting = core_resources.get("alerting")
    if alerting:
        parameters["sns_info_warning_topic_arn"] = _create_parameter(
            "sns-info-warning-topic-arn",
            f"{prefix}/sns/alerts/info-warning/arn",
            alerting.info_warning_topic.arn,
            "SNS topic ARN for info and warning alerts",
            tags
        )
        
        parameters["sns_error_topic_arn"] = _create_parameter(
            "sns-error-topic-arn",
            f"{prefix}/sns/alerts/error/arn",
            alerting.error_topic.arn,
            "SNS topic ARN for error alerts",
            tags
        )
    
    # Billing/Budget SNS Topic (created conditionally in billing_alarms)
    billing_topic = core_resources.get("billing_topic")
    if billing_topic:
        parameters["sns_billing_topic_arn"] = _create_parameter(
            "sns-billing-topic-arn",
            f"{prefix}/sns/alerts/billing/arn",
            billing_topic.arn,
            "SNS topic ARN for billing and budget alerts",
            tags
        )
    
    # Customer Profiles Parameters (if enabled)
    customer_profiles = core_resources.get("customer_profiles")
    if customer_profiles:
        domain = customer_profiles.get("domain")
        if domain:
            parameters["customer_profiles_domain_name"] = _create_parameter(
                "customer-profiles-domain-name",
                f"{prefix}/customer-profiles/domain/name",
                domain.domain_name,
                "Customer Profiles domain name",
                tags
            )
            
            parameters["customer_profiles_domain_arn"] = _create_parameter(
                "customer-profiles-domain-arn",
                f"{prefix}/customer-profiles/domain/arn",
                domain.arn,
                "Customer Profiles domain ARN",
                tags
            )
        
        # Error queue parameters (if enabled)
        error_queue = customer_profiles.get("error_queue")
        if error_queue:
            parameters["customer_profiles_error_queue_name"] = _create_parameter(
                "customer-profiles-error-queue-name",
                f"{prefix}/customer-profiles/error-queue/name",
                error_queue.name,
                "Customer Profiles error reporting queue name",
                tags
            )
            
            parameters["customer_profiles_error_queue_arn"] = _create_parameter(
                "customer-profiles-error-queue-arn",
                f"{prefix}/customer-profiles/error-queue/arn",
                error_queue.arn,
                "Customer Profiles error reporting queue ARN",
                tags
            )
    
    pulumi.log.info(f"Created {len(parameters)} Parameter Store items with prefix: {prefix}")
    
    return parameters


def _create_parameter(
    resource_name: str,
    parameter_name: str,
    value: pulumi.Output[str] | str,
    description: str,
    tags: Dict[str, str]
) -> aws.ssm.Parameter:
    """
    Create a single SSM Parameter Store item.
    
    Args:
        resource_name: Pulumi resource name
        parameter_name: SSM parameter name (full path)
        value: Parameter value (can be Output or string)
        description: Parameter description
        tags: Tags to apply to the parameter
        
    Returns:
        SSM Parameter resource
    """
    return aws.ssm.Parameter(
        resource_name,
        name=parameter_name,
        type="String",
        value=value,
        description=description,
        tags={
            **tags,
            "Name": resource_name,
            "ParameterStore": "true"
        }
    )


def export_parameter_store_info(parameters: Dict[str, aws.ssm.Parameter]) -> None:
    """
    Export information about created parameters as Pulumi outputs.
    
    This creates a convenient summary of all parameter store items
    that customers can reference.
    
    Args:
        parameters: Dictionary of parameter resources
    """
    # Export the count of parameters created
    pulumi.export("parameter_store_count", len(parameters))
    
    # Export the prefix for easy reference
    pulumi.export("parameter_store_prefix", "/elevai")
    
    # Export a list of all parameter names
    parameter_names = [param.name for param in parameters.values()]
    # pulumi.export("parameter_store_names", parameter_names)
