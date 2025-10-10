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
Core Infrastructure Module

This module contains all core Amazon Connect infrastructure components.
These are designed to be updated from the upstream repository without conflicts.
"""

from typing import Dict, Any
import pulumi

from .connect import create_connect_instance
from .s3 import create_s3_buckets
from .iam import create_iam_resources
from .lambda_functions import create_lambda_functions
from .qconnect import create_qconnect_integration, create_qconnect_knowledge_bucket
from .kms import create_connect_data_key

# Import alerting infrastructure
from .alerting import (
    create_alerting_infrastructure,
    create_lambda_alarms,
    create_connect_alarms,
    create_sqs_alarms,
    create_billing_alarms
)
from .parameter_store import create_parameter_store_items, export_parameter_store_info


def create_core_infrastructure(tags: Dict[str, str]) -> Dict[str, Any]:
    """
    Create all core infrastructure resources.
    
    Args:
        tags: Common tags to apply to all resources
        
    Returns:
        Dictionary containing references to created resources
    """
    resources = {}
    
    # Create alerting infrastructure first (SNS topics)
    alerting = create_alerting_infrastructure(tags)
    resources["alerting"] = alerting
    
    # Create KMS key first (needed by S3 buckets and Connect instance)
    kms_key = create_connect_data_key(tags)
    resources["kms_key"] = kms_key
    
    # Create IAM resources first (needed by other resources)
    iam_resources = create_iam_resources(tags)
    resources["iam"] = iam_resources
    
    # Create S3 buckets for recordings, reports, etc.
    s3_buckets = create_s3_buckets(tags, kms_key)
    resources["s3_buckets"] = s3_buckets
    
    # Create Amazon Connect instance and associate S3 buckets
    connect_instance, firehose, firehose_bucket = create_connect_instance(tags, s3_buckets, kms_key)
    resources["connect_instance"] = connect_instance
    resources["connect_instance_id"] = connect_instance.id
    resources["connect_instance_arn"] = connect_instance.arn
    resources["firehose"] = firehose
    resources["firehose_bucket"] = firehose_bucket
    
    
    # Create Lambda functions
    lambda_functions = create_lambda_functions(
        connect_instance=connect_instance,
        iam_role=iam_resources["lambda_role"],
        tags=tags
    )
    resources["lambda_functions"] = lambda_functions
    
    # Create Amazon Q (QConnect) integration (optional)
    config = pulumi.Config("qconnect")
    if config.get_bool("enabled") or False:
        # Create dedicated S3 bucket for knowledge base content and configuration
        # This single bucket contains both content files and the tagging config
        qconnect_kb_bucket = create_qconnect_knowledge_bucket(tags, kms_key, s3_buckets["logging"])
        resources["qconnect_kb_bucket"] = qconnect_kb_bucket
        
        # Create QConnect integration with content tagging
        qconnect_resources = create_qconnect_integration(
            connect_instance=connect_instance,
            knowledge_base_s3_bucket=qconnect_kb_bucket,
            kms_key=kms_key,
            tags=tags
        )
        resources["qconnect"] = qconnect_resources
    
    # Create CloudWatch alarms for all resources
    # Check if alerting is enabled (default: true)
    alerting_config = pulumi.Config("alerting")
    if alerting_config.get_bool("enabled") != False:  # Default to enabled
        # Lambda alarms
        if lambda_functions:
            create_lambda_alarms(lambda_functions, alerting)
        
        # Amazon Connect alarms
        create_connect_alarms(connect_instance, alerting)
        
        # Billing alarms (AWS Budgets)
        billing_resources = create_billing_alarms(tags, alerting)
        resources["billing_budgets"] = billing_resources.get("budgets", [])
        resources["billing_topic"] = billing_resources.get("topic")
        
        # Note: Add SQS alarms when SQS queues are created
        # create_sqs_alarms(sqs_queues, alerting)
    
    # Create Parameter Store items for external integrations
    # This provides a normalized interface for customers to extend the infrastructure
    parameter_store_items = create_parameter_store_items(resources, tags)
    resources["parameter_store"] = parameter_store_items
    
    # Export parameter store information
    export_parameter_store_info(parameter_store_items)
    
    return resources


__all__ = ["create_core_infrastructure"]
