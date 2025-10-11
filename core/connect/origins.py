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
Amazon Connect Approved Origins

Manages approved origins for CCP embedding.
"""

from typing import List
import pulumi
import pulumi_aws_native as aws_native
import pulumi_aws as aws


def create_approved_origins(
    connect_instance: aws.connect.Instance
) -> List[aws_native.connect.ApprovedOrigin]:
    """
    Create approved origins for Amazon Connect CCP embedding.
    
    Approved origins are URLs allowed to embed the Contact Control Panel (CCP).
    Required for web applications integrating the CCP widget.
    
    Args:
        connect_instance: The Amazon Connect instance
        
    Returns:
        List of created ApprovedOrigin resources
    """
    config = pulumi.Config("connect")
    approved_origins_config = config.get_object("approvedOrigins") or []
    
    if not approved_origins_config:
        pulumi.log.info("No approved origins configured.")
        return []
    
    approved_origin_resources = []
    
    for idx, origin_url in enumerate(approved_origins_config):
        if _is_valid_origin(origin_url):
            origin = _create_approved_origin(
                connect_instance, origin_url, idx
            )
            approved_origin_resources.append(origin)
    
    if approved_origin_resources:
        pulumi.export("approved_origins", [
            origin.origin for origin in approved_origin_resources
        ])
    
    return approved_origin_resources


def _is_valid_origin(origin_url: str) -> bool:
    """Validate origin URL format."""
    is_localhost = origin_url.startswith(("http://localhost", "http://127.0.0.1"))
    is_https = origin_url.startswith("https://")
    
    if not is_https and not is_localhost:
        pulumi.log.warn(
            f"Skipping invalid origin '{origin_url}': "
            f"Must use https:// (or http://localhost for local dev)"
        )
        return False
    
    return True


def _create_approved_origin(
    connect_instance: aws.connect.Instance,
    origin_url: str,
    idx: int
) -> aws_native.connect.ApprovedOrigin:
    """Create a single approved origin resource."""
    domain = origin_url.replace("https://", "").replace("/", "-").replace(".", "-").replace(":", "-")
    resource_name = f"approved-origin-{idx}-{domain}"
    
    instance_arn = connect_instance.arn.apply(lambda arn: arn.strip())
    
    approved_origin = aws_native.connect.ApprovedOrigin(
        resource_name,
        instance_id=instance_arn,
        origin=origin_url,
        opts=pulumi.ResourceOptions(depends_on=[connect_instance])
    )
    
    return approved_origin
