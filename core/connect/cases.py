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
Amazon Connect Cases Domain and Templates

A domain is a container for all case data, such as cases, fields, templates and layouts.
Each Amazon Connect instance can be associated with only one Cases domain.

Note: A valid Customer Profile domain is required before using Cases.
"""

from typing import Dict, Any
import pulumi
import pulumi_aws as aws
import pulumi_aws_native as aws_native

from core.utils.naming import create_name


def create_cases_domain(
    connect_instance_id: pulumi.Output[str],
    connect_instance_arn: pulumi.Output[str],
    customer_profiles_domain: Any,
    tags: Dict[str, str]
) -> Dict[str, Any]:
    """
    Create an Amazon Connect Cases domain and store configuration in Parameter Store.
    
    Args:
        connect_instance_id: The ID of the Amazon Connect instance
        connect_instance_arn: The ARN of the Amazon Connect instance
        customer_profiles_domain: Customer Profiles domain (required dependency)
        tags: Tags to apply to the domain
        
    Returns:
        Dictionary containing the Cases domain and related resources
    """
    domain_name = create_name("cases", "domain")
    
    # Create the Cases domain (depends on Customer Profiles)
    cases_domain = aws_native.cases.Domain(
        "cases-domain",
        name=domain_name,
        tags=[
            aws_native.TagArgs(
                key=key,
                value=value
            )
            for key, value in tags.items()
        ],
        opts=pulumi.ResourceOptions(
            depends_on=[customer_profiles_domain]
        )
    )
    
    # Associate the Cases domain with the Connect instance
    cases_integration = aws_native.connect.IntegrationAssociation(
        "cases-integration",
        instance_id=connect_instance_arn,
        integration_type=aws_native.connect.IntegrationAssociationIntegrationType.CASES_DOMAIN,
        integration_arn=cases_domain.domain_arn,
        opts=pulumi.ResourceOptions(
            depends_on=[cases_domain]
        )
    )
    
    # Store Cases domain information in Parameter Store
    prefix = "/elevai"
    
    domain_id_param = aws.ssm.Parameter(
        "cases-domain-id-param",
        name=f"{prefix}/cases/domain/id",
        type="String",
        value=cases_domain.domain_id,
        description="Amazon Connect Cases domain ID",
        tags={**tags, "Name": "cases-domain-id", "ParameterStore": "true"}
    )
    
    domain_name_param = aws.ssm.Parameter(
        "cases-domain-name-param",
        name=f"{prefix}/cases/domain/name",
        type="String",
        value=cases_domain.name,
        description="Amazon Connect Cases domain name",
        tags={**tags, "Name": "cases-domain-name", "ParameterStore": "true"}
    )
    
    domain_arn_param = aws.ssm.Parameter(
        "cases-domain-arn-param",
        name=f"{prefix}/cases/domain/arn",
        type="String",
        value=cases_domain.domain_arn,
        description="Amazon Connect Cases domain ARN",
        tags={**tags, "Name": "cases-domain-arn", "ParameterStore": "true"}
    )
    
    # Export domain information
    pulumi.export("cases_domain_id", cases_domain.domain_id)
    pulumi.export("cases_domain_arn", cases_domain.domain_arn)
    pulumi.export("cases_domain_name", cases_domain.name)
    pulumi.export("cases_domain_status", cases_domain.domain_status)
    pulumi.export("cases_integration_id", cases_integration.integration_association_id)
    
    return {
        "domain": cases_domain,
        "integration": cases_integration,
        "parameters": {
            "domain_id": domain_id_param,
            "domain_name": domain_name_param,
            "domain_arn": domain_arn_param,
        }
    }
