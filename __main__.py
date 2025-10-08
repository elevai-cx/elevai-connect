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
Pulumi Amazon Connect Infrastructure Project

Main entry point for the infrastructure deployment.
This file orchestrates the creation of core resources and custom extensions.
"""

import pulumi
from core import create_core_infrastructure
from custom import initialize_custom_resources


def main():
    """
    Main function to deploy infrastructure.
    
    Creates core Amazon Connect infrastructure and then initializes
    any custom resources defined in the custom/ directory.
    """
    # Get stack configuration
    config = pulumi.Config()
    stack_name = pulumi.get_stack()
    project_name = pulumi.get_project()
    
    # Create tags for all resources
    common_tags = {
        "Project": project_name,
        "Stack": stack_name,
        "ManagedBy": "Pulumi",
    }
    
    pulumi.log.info(f"Deploying {project_name} to stack: {stack_name}")
    
    # Deploy core infrastructure
    core_resources = create_core_infrastructure(common_tags)
    
    # Deploy custom resources (if any)
    custom_resources = initialize_custom_resources(core_resources, common_tags)
    
    # Export key outputs
    pulumi.export("connect_instance_id", core_resources.get("connect_instance_id"))
    pulumi.export("connect_instance_arn", core_resources.get("connect_instance_arn"))
    
    # Export SAML resources if using SAML identity management
    iam_resources = core_resources.get("iam", {})
    if "saml_provider" in iam_resources:
        pulumi.export("saml_provider_arn", iam_resources["saml_provider"].arn)
        pulumi.export("saml_role_arn", iam_resources["saml_role"].arn)
        pulumi.export("saml_role_name", iam_resources["saml_role"].name)


if __name__ == "__main__":
    main()
