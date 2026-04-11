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
Amplify App Infrastructure

Deploys the Elevai Toolkit via AWS Amplify using S3 manual deploys.

The Toolkit is a collection of standalone UI components (AudioPlayer, Banner, …)
embedded in Connect step-by-step guides via the Application view component.

Flow on every `pulumi up`:
  1. Hash all source files in toolkit/ — if nothing changed, steps 2-4 are skipped
  2. npm ci + npm run build  (pulumi_command, triggered by source hash)
  3. Zip dist/ → amplify-toolkit.zip  (pulumi_command, triggered by source hash)
  4. Upload zip to S3 via AWS CLI  (pulumi_command, triggered by source hash)
  5. Start Amplify manual deployment from S3  (pulumi_command, triggered by source hash)

Config (pulumi config set):
    amplify:branch   - Branch name to deploy (default: main)
"""

from typing import Dict, Any
import hashlib
import os
import pulumi
import pulumi_aws as aws
import pulumi_aws_native as aws_native
import pulumi_command as command


AMPLIFY_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "amplify-app")
TOOLKIT_DIR = os.path.join(AMPLIFY_ROOT, "toolkit")


def _hash_dir(directory: str) -> str:
    """
    Produce a stable hash of all source files in a directory,
    excluding node_modules, dist, .vite, and any .zip files.
    """
    hasher = hashlib.sha256()
    exclude_dirs = {"node_modules", "dist", ".vite"}

    for root, dirs, files in os.walk(directory):
        dirs[:] = sorted(d for d in dirs if d not in exclude_dirs)
        for filename in sorted(files):
            if filename.endswith(".zip"):
                continue
            filepath = os.path.join(root, filename)
            rel = os.path.relpath(filepath, directory)
            hasher.update(rel.encode())
            try:
                with open(filepath, "rb") as f:
                    hasher.update(f.read())
            except OSError:
                pass

    return hasher.hexdigest()


def create_amplify_app(
    connect_instance: aws.connect.Instance,
    tags: Dict[str, str],
) -> Dict[str, Any]:
    """
    Create the Amplify-hosted Elevai Toolkit for Connect step-by-step guides.

    Builds the Vite app locally, zips the output, uploads to S3, and triggers
    an Amplify manual deployment. Subsequent `pulumi up` calls only rebuild
    when source files in toolkit/ have changed.

    Args:
        connect_instance: The Amazon Connect instance resource
        tags: Tags to apply to all resources

    Returns:
        Dictionary of created resources
    """
    config = pulumi.Config("amplify")
    branch_name = config.get("branch") or "main"

    # -------------------------------------------------------------------------
    # IAM role for Amplify service
    # -------------------------------------------------------------------------
    amplify_role = aws.iam.Role(
        "amplify-service-role",
        assume_role_policy="""{
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": { "Service": "amplify.amazonaws.com" },
                "Action": "sts:AssumeRole"
            }]
        }""",
        tags={**tags, "Purpose": "AmplifyService"},
    )

    aws.iam.RolePolicyAttachment(
        "amplify-service-role-policy",
        role=amplify_role.name,
        policy_arn="arn:aws:iam::aws:policy/AdministratorAccess-Amplify",
    )

    # -------------------------------------------------------------------------
    # S3 bucket for Amplify deployment artifacts
    # ACLs must be enabled for Amplify manual S3 deploys
    # -------------------------------------------------------------------------
    deploy_bucket = aws.s3.Bucket(
        "amplify-deploy-bucket",
        tags={**tags, "Purpose": "AmplifyDeploy"},
    )

    ownership_controls = aws.s3.BucketOwnershipControls(
        "amplify-deploy-bucket-ownership",
        bucket=deploy_bucket.id,
        rule=aws.s3.BucketOwnershipControlsRuleArgs(
            object_ownership="BucketOwnerPreferred",
        ),
    )

    aws.s3.BucketAcl(
        "amplify-deploy-bucket-acl",
        bucket=deploy_bucket.id,
        acl="private",
        opts=pulumi.ResourceOptions(depends_on=[
            ownership_controls,
        ]),
    )

    aws.s3.BucketVersioning(
        "amplify-deploy-bucket-versioning",
        bucket=deploy_bucket.id,
        versioning_configuration=aws.s3.BucketVersioningVersioningConfigurationArgs(
            status="Enabled",
        ),
    )

    # =========================================================================
    # TOOLKIT — collection of standalone UI components (AudioPlayer, Banner, …)
    # Embedded in Connect step-by-step guides via the Application view component.
    # Query-param driven; no Connect SDK dependency.
    # =========================================================================
    toolkit_zip_path = os.path.join(TOOLKIT_DIR, "amplify-toolkit.zip")
    toolkit_dist_dir = os.path.join(TOOLKIT_DIR, "dist")
    toolkit_hash = _hash_dir(TOOLKIT_DIR)

    toolkit_amplify_app = aws.amplify.App(
        "toolkit-app",
        name="elevai-toolkit",
        iam_service_role_arn=amplify_role.arn,
        custom_rules=[
            aws.amplify.AppCustomRuleArgs(
                source="</^[^.]+$|\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json)$)([^.]+$)/>",
                target="/index.html",
                status="200",
            )
        ],
        tags={**tags, "Purpose": "ElevaiToolkit"},
    )

    toolkit_amplify_branch = aws.amplify.Branch(
        "toolkit-branch",
        app_id=toolkit_amplify_app.id,
        branch_name=branch_name,
        tags={**tags, "Purpose": "ElevaiToolkit"},
    )

    toolkit_amplify_url = pulumi.Output.all(
        toolkit_amplify_branch.branch_name, toolkit_amplify_app.default_domain
    ).apply(lambda args: f"https://{args[0]}.{args[1]}")

    aws_native.connect.ApprovedOrigin(
        "toolkit-approved-origin",
        instance_id=connect_instance.arn,
        origin=toolkit_amplify_url,
        opts=pulumi.ResourceOptions(depends_on=[connect_instance, toolkit_amplify_branch]),
    )

    # Build toolkit
    toolkit_build = command.local.Command(
        "toolkit-build",
        create=f"cd {TOOLKIT_DIR} && npm ci && npm run build",
        triggers=[toolkit_hash],
        opts=pulumi.ResourceOptions(depends_on=[toolkit_amplify_branch]),
    )

    # Zip toolkit dist
    toolkit_zip = command.local.Command(
        "toolkit-zip",
        create=f"cd {toolkit_dist_dir} && zip -r {toolkit_zip_path} .",
        triggers=[toolkit_hash],
        opts=pulumi.ResourceOptions(depends_on=[toolkit_build]),
    )

    # Upload toolkit zip to the shared S3 deploy bucket
    toolkit_upload_cmd = deploy_bucket.id.apply(
        lambda bucket_id: f"aws s3 cp {toolkit_zip_path} s3://{bucket_id}/amplify-toolkit.zip"
    )

    toolkit_upload = command.local.Command(
        "toolkit-upload",
        create=toolkit_upload_cmd,
        triggers=[toolkit_hash],
        opts=pulumi.ResourceOptions(depends_on=[toolkit_zip]),
    )

    # Deploy toolkit to Amplify from S3
    toolkit_deploy_cmd = pulumi.Output.all(
        toolkit_amplify_app.id,
        toolkit_amplify_branch.branch_name,
        deploy_bucket.id,
    ).apply(
        lambda args: (
            f"aws amplify start-deployment"
            f" --app-id {args[0]}"
            f" --branch-name {args[1]}"
            f" --source-url s3://{args[2]}/amplify-toolkit.zip"
        )
    )

    command.local.Command(
        "toolkit-deploy",
        create=toolkit_deploy_cmd,
        triggers=[toolkit_hash, toolkit_upload.stdout],
        opts=pulumi.ResourceOptions(depends_on=[toolkit_upload]),
    )

    # Register toolkit in AppIntegrations
    toolkit_integration = aws_native.appintegrations.Application(
        "toolkit-integration",
        name="Elevai Toolkit",
        namespace="elevai-toolkit",
        description="Reusable UI components for Connect step-by-step guides and external apps",
        application_source_config=aws_native.appintegrations.ApplicationSourceConfigPropertiesArgs(
            external_url_config=aws_native.appintegrations.ApplicationExternalUrlConfigArgs(
                access_url=toolkit_amplify_url,
                approved_origins=[toolkit_amplify_url],
            ),
        ),
        application_config=aws_native.appintegrations.ApplicationConfigArgs(
            contact_handling=aws_native.appintegrations.ApplicationContactHandlingArgs(
                scope="PER_CONTACT",
            ),
        ),
        permissions=["*"],
        iframe_config=aws_native.appintegrations.ApplicationIframeConfigArgs(
            allow=[
                "clipboard-read",
                "clipboard-write",
            ],
            sandbox=[
                "allow-forms",
                "allow-modals",
                "allow-popups",
                "allow-popups-to-escape-sandbox",
                "allow-same-origin",
                "allow-scripts",
            ],
        ),
        tags=[aws_native.TagArgs(key=k, value=v) for k, v in {**tags, "Purpose": "ElevaiToolkit"}.items()],
        opts=pulumi.ResourceOptions(depends_on=[toolkit_amplify_branch]),
    )

    # Associate toolkit with the Connect instance
    aws_native.connect.IntegrationAssociation(
        "toolkit-instance-association",
        instance_id=connect_instance.arn,
        integration_type=aws_native.connect.IntegrationAssociationIntegrationType.APPLICATION,
        integration_arn=toolkit_integration.application_arn,
        opts=pulumi.ResourceOptions(depends_on=[toolkit_integration]),
    )

    pulumi.export("amplify_toolkit_url", toolkit_amplify_url)
    pulumi.export("amplify_deploy_bucket", deploy_bucket.id)

    return {
        "app": toolkit_amplify_app,
        "branch": toolkit_amplify_branch,
        "role": amplify_role,
        "deploy_bucket": deploy_bucket,
        "url": toolkit_amplify_url,
    }
