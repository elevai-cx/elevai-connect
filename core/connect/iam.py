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
IAM Roles and Policies

Creates IAM roles and policies with least-privilege access for Amazon Connect resources.
"""

from typing import Dict
import pulumi
import pulumi_aws as aws
import json
from ..post_deployment_tracker import add_manual_step


def create_iam_resources(tags: Dict[str, str]) -> Dict[str, any]:
    """
    Create IAM roles and policies for Amazon Connect infrastructure.
    
    Args:
        tags: Tags to apply to all IAM resources
        
    Returns:
        Dictionary of role names to role resources and identity providers
    """
    resources = {}
    
    # Lambda execution role
    lambda_role = create_lambda_role(tags)
    resources["lambda_role"] = lambda_role
    
    # Connect service role
    connect_role = create_connect_service_role(tags)
    resources["connect_role"] = connect_role
    
    # SAML resources (only if using SAML identity management)
    config = pulumi.Config("connect")
    identity_management_type = config.get("identityManagementType") or "CONNECT_MANAGED"
    
    if identity_management_type == "SAML":
        saml_resources = create_saml_resources(tags)
        resources["saml_provider"] = saml_resources["provider"]
        resources["saml_role"] = saml_resources["role"]
    
    return resources


def create_lambda_role(tags: Dict[str, str]) -> aws.iam.Role:
    """
    Create IAM role for the Connect Utils Lambda function.
    
    This role is specifically for the utils Lambda that handles contact flow operations.
    Other Lambda functions (like content-tagger) have their own dedicated roles.
    
    Args:
        tags: Tags to apply to the role
        
    Returns:
        Utils Lambda execution role
    """
    # Create assume role policy
    assume_role_policy = aws.iam.get_policy_document(
        statements=[
            aws.iam.GetPolicyDocumentStatementArgs(
                effect="Allow",
                principals=[
                    aws.iam.GetPolicyDocumentStatementPrincipalArgs(
                        type="Service",
                        identifiers=["lambda.amazonaws.com"],
                    )
                ],
                actions=["sts:AssumeRole"],
            )
        ]
    )
    
    # Create role
    lambda_role = aws.iam.Role(
        "connect-utils-lambda-role",
        assume_role_policy=assume_role_policy.json,
        tags={**tags, "Purpose": "ConnectUtilsLambda"},
    )
    
    # Attach AWS managed policy for basic Lambda execution (CloudWatch Logs)
    aws.iam.RolePolicyAttachment(
        "connect-utils-lambda-basic-execution",
        role=lambda_role.name,
        policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    )
    
    # Create custom policy for the Connect Utils Lambda function
    # This policy grants permissions for:
    # - S3: Access to Connect recordings and storage buckets
    # - Connect: Contact recording, attributes, and metadata operations
    # - QConnect: Amazon Q session management for agent assistance
    lambda_policy = aws.iam.RolePolicy(
        "connect-utils-lambda-custom-policy",
        role=lambda_role.id,
        policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "QConnectSessionManagement",
                    "Effect": "Allow",
                    "Action": [
                        "connect:DescribeContact",
                        "wisdom:UpdateSession"
                    ],
                    "Resource": "*",
                },
            ],
        }),
    )
    
    return lambda_role


def create_connect_service_role(tags: Dict[str, str]) -> aws.iam.Role:
    """
    Create IAM role for Amazon Connect service.
    
    Args:
        tags: Tags to apply to the role
        
    Returns:
        Connect service role
    """
    # Create assume role policy
    assume_role_policy = aws.iam.get_policy_document(
        statements=[
            aws.iam.GetPolicyDocumentStatementArgs(
                effect="Allow",
                principals=[
                    aws.iam.GetPolicyDocumentStatementPrincipalArgs(
                        type="Service",
                        identifiers=["connect.amazonaws.com"],
                    )
                ],
                actions=["sts:AssumeRole"],
            )
        ]
    )
    
    # Create role
    connect_role = aws.iam.Role(
        "connect-service-role",
        assume_role_policy=assume_role_policy.json,
        tags={**tags, "Purpose": "ConnectService"},
    )
    
    # Create policy for S3 access (recordings, etc.)
    connect_policy = aws.iam.RolePolicy(
        "connect-service-policy",
        role=connect_role.id,
        policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:PutObject",
                        "s3:PutObjectAcl",
                        "s3:GetObject",
                        "s3:GetObjectAcl",
                    ],
                    "Resource": "arn:aws:s3:::*",
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "kinesis:PutRecord",
                        "kinesis:PutRecords",
                    ],
                    "Resource": "*",
                },
            ],
        }),
    )
    
    return connect_role


def get_placeholder_saml_metadata() -> str:
    """
    Get placeholder SAML metadata for initial deployment.
    
    This is a minimal valid SAML 2.0 metadata document that AWS IAM will accept.
    It uses the Baltimore CyberTrust Root certificate as a placeholder.
    
    After deployment, update the SAML provider with your actual IdP metadata via:
    - AWS Console (IAM > Identity Providers)
    - AWS CLI: ./update-saml-metadata.sh your-metadata.xml
    - Direct API call
    
    Returns:
        Valid SAML 2.0 metadata XML string
    """
    return """<?xml version="1.0" encoding="UTF-8"?>
<EntityDescriptor xmlns="urn:oasis:names:tc:SAML:2.0:metadata" entityID="https://placeholder.example.com/saml">
  <IDPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <KeyDescriptor use="signing">
      <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
        <ds:X509Data>
          <ds:X509Certificate>MIIDdzCCAl+gAwIBAgIEAgAAuTANBgkqhkiG9w0BAQUFADBaMQswCQYDVQQGEwJJ
RTESMBAGA1UEChMJQmFsdGltb3JlMRMwEQYDVQQLEwpDeWJlclRydXN0MSIwIAYD
VQQDExlCYWx0aW1vcmUgQ3liZXJUcnVzdCBSb290MB4XDTAwMDUxMjE4NDYwMFoX
DTI1MDUxMjIzNTkwMFowWjELMAkGA1UEBhMCSUUxEjAQBgNVBAoTCUJhbHRpbW9y
ZTETMBEGA1UECxMKQ3liZXJUcnVzdDEiMCAGA1UEAxMZQmFsdGltb3JlIEN5YmVy
VHJ1c3QgUm9vdDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAKMEuyKr
mD1X6CZymrV51Cni4eiVgLGw41uOKymaZN+hXe2wCQVt2yguzmKiYv60iNoS6zjr
IZ3AQSsBUnuId9Mcj8e6uYi1agnnc+gRQKfRzMpijS3ljwumUNKoUMMo6vWrJYeK
mpYcqWe4PwzV9/lSEy/CG9VwcPCPwBLKBsua4dnKM3p31vjsufFoREJIE9LAwqSu
XmD+tqYF/LTdB1kC1FkYmGP1pWPgkAx9XbIGevOF6uvUA65ehD5f/xXtabz5OTZy
dc93Uk3zyZAsuT3lySNTPx8kmCFcB5kpvcY67Oduhjprl3RjM71oGDHweI12v/ye
jl0qhqdNkNwnGjkCAwEAAaNFMEMwHQYDVR0OBBYEFOWdWTCCR1jMrPoIVDaGezq1
BE3wMBIGA1UdEwEB/wQIMAYBAf8CAQMwDgYDVR0PAQH/BAQDAgEGMA0GCSqGSIb3
DQEBBQUAA4IBAQCFDF2O5G9RaEIFoN27TyclhAO992T9Ldcw46QQF+vaKSm2eT92
9hkTI7gQCvlYpNRhcL0EYWoSihfVCr3FvDB81ukMJY2GQE/szKN+OMY3EU/t3Wgx
jkzSswF07r51XgdIGn9w/xZchMB5hbgF/X++ZRGjD8ACtPhSNzkE1akxehi/oCr0
Epn3o0WC4zxe9Z2etciefC7IpJ5OCBRLbf1wbWsaY71k5h+3zvDyny67G7fyUIhz
ksLi4xaNmjICq44Y3ekQEe5+NauQrz4wlHrQMz2nZQ/1/I6eYs9HRCwBXbsdtTLS
R9I4LtD+gdwyah617jzV/OeBHRnDJELqYzmp</ds:X509Certificate>
        </ds:X509Data>
      </ds:KeyInfo>
    </KeyDescriptor>
    <NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</NameIDFormat>
    <SingleSignOnService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" Location="https://placeholder.example.com/sso/saml"/>
    <SingleSignOnService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect" Location="https://placeholder.example.com/sso/saml"/>
  </IDPSSODescriptor>
</EntityDescriptor>"""


def create_saml_resources(tags: Dict[str, str]) -> Dict[str, any]:
    """
    Create IAM SAML identity provider and role for Amazon Connect SAML authentication.
    
    This creates:
    1. SAML Identity Provider - connects AWS to your external IdP (e.g., Okta, Azure AD)
    2. SAML Role - allows federated users to assume access to Amazon Connect
    
    The SAML metadata can be provided via:
    - Config parameter: connect:samlMetadataFile (path to metadata XML file)
    - If not provided: Uses placeholder metadata (update later via AWS Console/CLI)
    
    Args:
        tags: Tags to apply to the resources
        
    Returns:
        Dictionary containing the SAML provider and role
    """
    import os
    
    config = pulumi.Config("connect")
    metadata_file = config.get("samlMetadataFile")
    
    # Try to load metadata from file if specified
    if metadata_file:
        # Handle both absolute and relative paths
        if not os.path.isabs(metadata_file):
            # Get the project root directory
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            metadata_file = os.path.join(project_root, metadata_file)
        
        if os.path.exists(metadata_file):
            pulumi.log.info(f"Using SAML metadata from file: {metadata_file}")
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    saml_metadata = f.read()
                pulumi.log.info("✅ Successfully loaded SAML metadata from file")
            except Exception as e:
                pulumi.log.warn(f"Failed to read SAML metadata file: {e}")
                pulumi.log.warn("Falling back to placeholder metadata")
                saml_metadata = get_placeholder_saml_metadata()
        else:
            pulumi.log.warn(f"SAML metadata file not found: {metadata_file}")
            pulumi.log.warn("Falling back to placeholder metadata")
            saml_metadata = get_placeholder_saml_metadata()
    else:
        pulumi.log.info("Using SAML placeholder metadata")
        saml_metadata = get_placeholder_saml_metadata()
        
        # Register manual step to update SAML metadata
        add_manual_step(
            title="Update SAML Identity Provider metadata with your IdP's metadata",
            doc_link="docs/POST_DEPLOYMENT_STEPS.md#2-saml-authentication-setup",
            details={"Provider Name": "ConnectSAMLProvider"}
        )
    
    # Create SAML Identity Provider
    saml_provider = aws.iam.SamlProvider(
        "connect-saml-provider",
        name="ConnectSAMLProvider",
        saml_metadata_document=saml_metadata,
        tags={**tags, "Purpose": "ConnectSAMLAuth"},
        opts=pulumi.ResourceOptions(
            # The SAML metadata is deployed as a placeholder and then updated
            # manually via the AWS console with the real IdP metadata.
            # Ignore changes so refresh/up don't revert the user's update.
            ignore_changes=["saml_metadata_document"],
        ),
    )
    
    # Create trust policy for the SAML role
    # This allows the SAML provider to assume the role
    saml_trust_policy = saml_provider.arn.apply(
        lambda provider_arn: aws.iam.get_policy_document(
            statements=[
                aws.iam.GetPolicyDocumentStatementArgs(
                    effect="Allow",
                    principals=[
                        aws.iam.GetPolicyDocumentStatementPrincipalArgs(
                            type="Federated",
                            identifiers=[provider_arn],
                        )
                    ],
                    actions=["sts:AssumeRoleWithSAML"],
                    conditions=[
                        aws.iam.GetPolicyDocumentStatementConditionArgs(
                            test="StringEquals",
                            variable="SAML:aud",
                            values=["https://signin.aws.amazon.com/saml"],
                        )
                    ],
                )
            ]
        ).json
    )
    
    # Create IAM role for SAML federated users
    saml_role = aws.iam.Role(
        "connect-saml-role",
        name="ConnectSAMLRole",
        assume_role_policy=saml_trust_policy,
        tags={**tags, "Purpose": "ConnectSAMLAccess"},
    )
    
    # Attach Amazon Connect federated access policy
    # This grants ONLY the permission to SSO into the Connect instance
    # Users get their actual Connect permissions from the Connect user/security profile config
    saml_policy = aws.iam.RolePolicy(
        "connect-saml-policy",
        role=saml_role.id,
        policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "connect:GetFederationToken",
                    ],
                    "Resource": "*",
                },
            ],
        }),
    )
    
    return {
        "provider": saml_provider,
        "role": saml_role,
    }
