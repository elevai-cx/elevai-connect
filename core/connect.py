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
Amazon Connect Instance Resources

Creates and configures the Amazon Connect contact center instance.
"""

from typing import Dict, Optional, List
import pulumi
import pulumi_aws as aws
import pulumi_aws_native as aws_native
import pulumi_command as command
import json
import re


def create_connect_instance(
    tags: Dict[str, str],
    s3_buckets: Dict[str, aws.s3.Bucket],
    kms_key: aws.kms.Key,
    enable_data_lake: bool = True
) -> tuple[aws.connect.Instance, aws.kinesis.FirehoseDeliveryStream, aws.s3.Bucket]:
    """
    Create an Amazon Connect instance with S3 storage associations.
    
    Args:
        tags: Tags to apply to the instance
        s3_buckets: Dictionary of S3 buckets to associate with the instance (must include 'logging' bucket)
        kms_key: KMS key for data encryption
        enable_data_lake: Whether to enable the Amazon Connect analytics data lake (default: True)
        
    Returns:
        Tuple of (Amazon Connect instance, Firehose delivery stream, Firehose S3 bucket)
    """
    config = pulumi.Config("connect")
    
    # Get configuration with defaults
    instance_alias = config.get("instanceAlias")
    if not instance_alias:
        raise ValueError("instanceAlias is required in Pulumi config")
    
    # Validate instance alias format
    validate_instance_alias(instance_alias)
    
    identity_management_type = config.get("identityManagementType") or "SAML"
    inbound_calls_enabled = config.get_bool("inboundCallsEnabled")
    if inbound_calls_enabled is None:
        inbound_calls_enabled = True
    
    outbound_calls_enabled = config.get_bool("outboundCallsEnabled")
    if outbound_calls_enabled is None:
        outbound_calls_enabled = True
    
    multi_party_conference_enabled = config.get_bool("multiPartyConferenceEnabled")
    if multi_party_conference_enabled is None:
        multi_party_conference_enabled = True
    
    contact_flow_logs_enabled = config.get_bool("contactFlowLogsEnabled")
    if contact_flow_logs_enabled is None:
        contact_flow_logs_enabled = True
    
    # Get logging bucket from s3_buckets
    if "logging" not in s3_buckets:
        raise ValueError("logging bucket must be provided in s3_buckets dictionary")
    logging_bucket = s3_buckets["logging"]
    
    # Create Firehose BEFORE the Connect instance
    firehose, firehose_bucket = create_contact_flow_logs_firehose(tags, kms_key, logging_bucket)
    
    # Create CloudWatch log group BEFORE the Connect instance if logging is enabled
    # Amazon Connect will use this existing log group
    log_group = None
    if contact_flow_logs_enabled:
        log_group = configure_log_retention(instance_alias, tags)
    
    # Prepare dependencies for Connect instance
    depends_on_resources = [firehose]
    if log_group:
        depends_on_resources.append(log_group)
    
    # Create the Amazon Connect instance
    connect_instance = aws.connect.Instance(
        "connect-instance",
        identity_management_type=identity_management_type,
        inbound_calls_enabled=inbound_calls_enabled,
        outbound_calls_enabled=outbound_calls_enabled,
        instance_alias=instance_alias,
        tags={**tags, "Name": f"{instance_alias}-connect-instance"},
        multi_party_conference_enabled=multi_party_conference_enabled,
        contact_flow_logs_enabled=contact_flow_logs_enabled,
        # Add explicit dependencies to ensure proper ordering
        opts=pulumi.ResourceOptions(depends_on=depends_on_resources)
    )
    
    # Create storage config for contact trace records AFTER instance is created
    aws.connect.InstanceStorageConfig(
        "contact-trace-records",
        instance_id=connect_instance.id,
        resource_type="CONTACT_TRACE_RECORDS",
        storage_config=aws.connect.InstanceStorageConfigStorageConfigArgs(
            storage_type="KINESIS_FIREHOSE",
            kinesis_firehose_config=aws.connect.InstanceStorageConfigStorageConfigKinesisFirehoseConfigArgs(
                firehose_arn=firehose.arn,
            ),
        ),
        opts=pulumi.ResourceOptions(depends_on=[connect_instance, firehose])
    )
    
    # Associate S3 buckets with Connect instance
    associate_s3_buckets(connect_instance, s3_buckets, kms_key)
    
    pulumi.export("connect_instance_id", connect_instance.id)
    pulumi.export("connect_instance_arn", connect_instance.arn)
    pulumi.export("connect_instance_status", connect_instance.status)
    pulumi.export("connect_instance_url", 
                 pulumi.Output.concat("https://", instance_alias, ".my.connect.aws"))
    pulumi.export("firehose_arn", firehose.arn)
    
    # Create approved origins for CCP embedding
    approved_origins = create_approved_origins(connect_instance)
    
    # Set up analytics data lake if enabled
    if enable_data_lake:
        data_lake_setup = setup_analytics_data_lake(connect_instance, tags=tags)
    
    return connect_instance, firehose, firehose_bucket


def validate_instance_alias(alias: str) -> None:
    """
    Validate the Amazon Connect instance alias format.
    
    Amazon Connect has undocumented requirements for instance alias formats.
    Based on empirical testing:
    - Works: name-region-env (e.g., "elevai-euw2-dev")
    - Fails: name-env-region (e.g., "elevai-dev-euw2")
    
    The alias should follow the pattern: <name>-<region>-<environment>
    
    Args:
        alias: The instance alias to validate
        
    Raises:
        ValueError: If the alias doesn't meet requirements
    """
    if not alias:
        raise ValueError("Instance alias cannot be empty")
    
    # Basic validation
    if len(alias) < 1 or len(alias) > 64:
        raise ValueError(f"Instance alias must be between 1 and 64 characters. Got: {len(alias)}")
    
    # Must start with a letter
    if not alias[0].isalpha():
        raise ValueError(f"Instance alias must start with a letter. Got: '{alias}'")
    
    # Can only contain lowercase letters, numbers, and hyphens
    if not re.match(r'^[a-z0-9-]+$', alias):
        raise ValueError(
            f"Instance alias can only contain lowercase letters, numbers, and hyphens. Got: '{alias}'"
        )
    
    # Cannot end with a hyphen
    if alias.endswith('-'):
        raise ValueError(f"Instance alias cannot end with a hyphen. Got: '{alias}'")
    
    # Cannot have consecutive hyphens
    if '--' in alias:
        raise ValueError(f"Instance alias cannot contain consecutive hyphens. Got: '{alias}'")
    
    # Warning about common format issues
    parts = alias.split('-')
    if len(parts) >= 3:
        # Check if it looks like name-env-region pattern (which fails)
        last_part = parts[-1]
        second_last = parts[-2] if len(parts) >= 2 else ""
        
        # Common environment names
        env_names = ['dev', 'test', 'staging', 'prod', 'production']
        # Common region abbreviations
        region_abbrevs = ['euw1', 'euw2', 'euw3', 'use1', 'use2', 'usw1', 'usw2']
        
        if second_last in env_names and last_part in region_abbrevs:
            pulumi.log.warn(
                f"Instance alias '{alias}' appears to use pattern 'name-env-region'. "
                f"This format has been known to fail. Consider using 'name-region-env' instead. "
                f"Example: Change '{alias}' to '{'-'.join(parts[:-2] + [last_part, second_last])}'"
            )


def associate_s3_buckets(
    connect_instance: aws.connect.Instance,
    s3_buckets: Dict[str, aws.s3.Bucket],
    kms_key: aws.kms.Key
) -> None:
    """
    Associate S3 buckets with the Amazon Connect instance for different storage types.
    
    Args:
        connect_instance: The Amazon Connect instance
        s3_buckets: Dictionary of S3 buckets to associate
        kms_key: KMS key for data encryption
    """
    
    # Associate Call Recordings bucket
    if "recordings" in s3_buckets:
        aws.connect.InstanceStorageConfig(
            "call-recordings-storage",
            instance_id=connect_instance.id,
            resource_type="CALL_RECORDINGS",
            storage_config=aws.connect.InstanceStorageConfigStorageConfigArgs(
                storage_type="S3",
                s3_config=aws.connect.InstanceStorageConfigStorageConfigS3ConfigArgs(
                    bucket_name=s3_buckets["recordings"].id,
                    bucket_prefix="call-recordings",
                    encryption_config=aws.connect.InstanceStorageConfigStorageConfigS3ConfigEncryptionConfigArgs(
                        encryption_type="KMS",
                        key_id=kms_key.arn,
                    ),
                ),
            ),
            opts=pulumi.ResourceOptions(depends_on=[connect_instance])
        )
    
    # Associate Chat Transcripts bucket
    if "chat_transcripts" in s3_buckets:
        aws.connect.InstanceStorageConfig(
            "chat-transcripts-storage",
            instance_id=connect_instance.id,
            resource_type="CHAT_TRANSCRIPTS",
            storage_config=aws.connect.InstanceStorageConfigStorageConfigArgs(
                storage_type="S3",
                s3_config=aws.connect.InstanceStorageConfigStorageConfigS3ConfigArgs(
                    bucket_name=s3_buckets["chat_transcripts"].id,
                    bucket_prefix="chat-transcripts",
                    encryption_config=aws.connect.InstanceStorageConfigStorageConfigS3ConfigEncryptionConfigArgs(
                        encryption_type="KMS",
                        key_id=kms_key.arn,
                    ),
                ),
            ),
            opts=pulumi.ResourceOptions(depends_on=[connect_instance])
        )
    
    # Associate Exported Reports bucket (SCHEDULED_REPORTS)
    if "exported_reports" in s3_buckets:
        aws.connect.InstanceStorageConfig(
            "exported-reports-storage",
            instance_id=connect_instance.id,
            resource_type="SCHEDULED_REPORTS",
            storage_config=aws.connect.InstanceStorageConfigStorageConfigArgs(
                storage_type="S3",
                s3_config=aws.connect.InstanceStorageConfigStorageConfigS3ConfigArgs(
                    bucket_name=s3_buckets["exported_reports"].id,
                    bucket_prefix="exported-reports",
                    encryption_config=aws.connect.InstanceStorageConfigStorageConfigS3ConfigEncryptionConfigArgs(
                        encryption_type="KMS",
                        key_id=kms_key.arn,
                    ),
                ),
            ),
            opts=pulumi.ResourceOptions(depends_on=[connect_instance])
        )
    
    # Associate Attachments bucket
    if "attachments" in s3_buckets:
        aws.connect.InstanceStorageConfig(
            "attachments-storage",
            instance_id=connect_instance.id,
            resource_type="ATTACHMENTS",
            storage_config=aws.connect.InstanceStorageConfigStorageConfigArgs(
                storage_type="S3",
                s3_config=aws.connect.InstanceStorageConfigStorageConfigS3ConfigArgs(
                    bucket_name=s3_buckets["attachments"].id,
                    bucket_prefix="attachments",
                    encryption_config=aws.connect.InstanceStorageConfigStorageConfigS3ConfigEncryptionConfigArgs(
                        encryption_type="KMS",
                        key_id=kms_key.arn,
                    ),
                ),
            ),
            opts=pulumi.ResourceOptions(depends_on=[connect_instance])
        )
    
    # Associate Screen Recordings bucket
    if "screen_recordings" in s3_buckets:
        aws.connect.InstanceStorageConfig(
            "screen-recordings-storage",
            instance_id=connect_instance.id,
            resource_type="SCREEN_RECORDINGS",
            storage_config=aws.connect.InstanceStorageConfigStorageConfigArgs(
                storage_type="S3",
                s3_config=aws.connect.InstanceStorageConfigStorageConfigS3ConfigArgs(
                    bucket_name=s3_buckets["screen_recordings"].id,
                    bucket_prefix="screen-recordings",
                    encryption_config=aws.connect.InstanceStorageConfigStorageConfigS3ConfigEncryptionConfigArgs(
                        encryption_type="KMS",
                        key_id=kms_key.arn,
                    ),
                ),
            ),
            opts=pulumi.ResourceOptions(depends_on=[connect_instance])
        )
    
    # Associate Contact Evaluations bucket
    if "contact_evaluations" in s3_buckets:
        aws.connect.InstanceStorageConfig(
            "contact-evaluations-storage",
            instance_id=connect_instance.id,
            resource_type="CONTACT_EVALUATIONS",
            storage_config=aws.connect.InstanceStorageConfigStorageConfigArgs(
                storage_type="S3",
                s3_config=aws.connect.InstanceStorageConfigStorageConfigS3ConfigArgs(
                    bucket_name=s3_buckets["contact_evaluations"].id,
                    bucket_prefix="contact-evaluations",
                    encryption_config=aws.connect.InstanceStorageConfigStorageConfigS3ConfigEncryptionConfigArgs(
                        encryption_type="KMS",
                        key_id=kms_key.arn,
                    ),
                ),
            ),
            opts=pulumi.ResourceOptions(depends_on=[connect_instance])
        )
    
    # Associate Email Messages bucket
    if "email_messages" in s3_buckets:
        aws.connect.InstanceStorageConfig(
            "email-messages-storage",
            instance_id=connect_instance.id,
            resource_type="EMAIL_MESSAGES",
            storage_config=aws.connect.InstanceStorageConfigStorageConfigArgs(
                storage_type="S3",
                s3_config=aws.connect.InstanceStorageConfigStorageConfigS3ConfigArgs(
                    bucket_name=s3_buckets["email_messages"].id,
                    bucket_prefix="email-messages",
                    encryption_config=aws.connect.InstanceStorageConfigStorageConfigS3ConfigEncryptionConfigArgs(
                        encryption_type="KMS",
                        key_id=kms_key.arn,
                    ),
                ),
            ),
            opts=pulumi.ResourceOptions(depends_on=[connect_instance])
        )


def configure_log_retention(
    instance_alias: str,
    tags: Dict[str, str]
) -> aws.cloudwatch.LogGroup:
    """
    Create CloudWatch log group for Amazon Connect logs BEFORE the instance is created.
    
    Amazon Connect will use this existing log group when contactFlowLogsEnabled is True.
    This approach ensures the log group exists with the desired retention settings from the start.
    
    Args:
        instance_alias: The instance alias used to construct the log group name
        tags: Tags to apply to the log group
        
    Returns:
        The created CloudWatch log group
    """
    config = pulumi.Config("cloudwatch")
    log_retention_days = config.get_int("logRetentionDays")
    
    # Default to 30 days if not specified
    if log_retention_days is None:
        log_retention_days = 30
    
    # Construct log group name - Amazon Connect expects log groups with this pattern
    log_group_name = f"/aws/connect/{instance_alias}"
    
    # If retention is 0, set to None (never expire)
    # Otherwise use the specified number of days
    retention_in_days = None if log_retention_days == 0 else log_retention_days
    
    # Create the log group BEFORE Amazon Connect instance
    # Amazon Connect will use this existing log group instead of creating a new one
    log_group = aws.cloudwatch.LogGroup(
        "connect-log-group",
        name=log_group_name,
        retention_in_days=retention_in_days,
        tags={**tags, "Purpose": "ConnectContactFlowLogs"}
    )
    
    pulumi.export("connect_log_group_name", log_group.name)
    if retention_in_days:
        pulumi.export("connect_log_retention_days", retention_in_days)
    else:
        pulumi.export("connect_log_retention_days", "Never expire")
    
    return log_group


def create_approved_origins(connect_instance: aws.connect.Instance) -> List[aws_native.connect.ApprovedOrigin]:
    """
    Create approved origins for Amazon Connect CCP embedding.
    
    Approved origins are URLs that are allowed to embed the Connect Contact Control Panel (CCP).
    This is required for web applications that need to integrate the CCP widget.
    
    Args:
        connect_instance: The Amazon Connect instance
        
    Returns:
        List of created ApprovedOrigin resources
    """
    config = pulumi.Config("connect")
    approved_origins_config = config.get_object("approvedOrigins") or []
    
    if not approved_origins_config:
        pulumi.log.info("No approved origins configured. Skipping approved origins setup.")
        return []
    
    approved_origin_resources = []
    
    for idx, origin_url in enumerate(approved_origins_config):
        # Validate origin URL
        # Allow http://localhost for local development, but require https for all other domains
        is_localhost = origin_url.startswith("http://localhost") or origin_url.startswith("http://127.0.0.1")
        is_https = origin_url.startswith("https://")
        
        if not is_https and not is_localhost:
            pulumi.log.warn(
                f"Skipping invalid origin '{origin_url}': Must use https:// protocol (or http://localhost for local development)"
            )
            continue
        
        # Create a resource name based on the URL (sanitize for Pulumi resource naming)
        domain = origin_url.replace("https://", "").replace("/", "-").replace(".", "-").replace(":", "-")
        resource_name = f"approved-origin-{idx}-{domain}"
        
        # Create the approved origin using aws_native provider
        # The InstanceId parameter expects the full ARN from connect_instance.arn
        # ARN format: arn:aws:connect:region:account-id:instance/instance-id
        # Pattern: ^arn:aws[-a-z0-9]*:connect:[-a-z0-9]*:[0-9]{12}:instance/[-a-zA-Z0-9]*$
        
        # Ensure ARN is properly formatted by applying a transformation
        def ensure_arn_format(arn: str) -> str:
            """Ensure ARN is in the correct format and strip any whitespace."""
            return arn.strip()
        
        instance_arn = connect_instance.arn.apply(ensure_arn_format)
        
        approved_origin = aws_native.connect.ApprovedOrigin(
            resource_name,
            instance_id=instance_arn,
            origin=origin_url,
            opts=pulumi.ResourceOptions(depends_on=[connect_instance])
        )
        
        approved_origin_resources.append(approved_origin)
        pulumi.log.info(f"Created approved origin: {origin_url}")
    
    # Export the approved origins for reference
    if approved_origin_resources:
        pulumi.export("approved_origins", [
            origin.origin for origin in approved_origin_resources
        ])
    
    return approved_origin_resources


def create_contact_flow_logs_firehose(tags: Dict[str, str], kms_key: aws.kms.Key, logging_bucket: aws.s3.Bucket) -> tuple[aws.kinesis.FirehoseDeliveryStream, aws.s3.Bucket]:
    """
    Create Kinesis Firehose for contact flow logs.
    
    Args:
        tags: Tags to apply to resources
        kms_key: KMS key for data encryption
        logging_bucket: S3 bucket to store access logs
        
    Returns:
        Tuple of (Kinesis Firehose delivery stream, S3 bucket)
    """
    # Create S3 bucket for logs with Object Lock enabled
    log_bucket = aws.s3.Bucket(
        "contact-records",
        object_lock_enabled=True,
        tags={**tags, "Purpose": "ContactFlowLogs"},
    )
    
    # Enable versioning
    aws.s3.BucketVersioning(
        "contact-records-versioning",
        bucket=log_bucket.id,
        versioning_configuration=aws.s3.BucketVersioningVersioningConfigurationArgs(
            status="Enabled",
        ),
    )
    
    # Enable KMS encryption using customer-managed key
    aws.s3.BucketServerSideEncryptionConfiguration(
        "contact-records-encryption",
        bucket=log_bucket.id,
        rules=[
            aws.s3.BucketServerSideEncryptionConfigurationRuleArgs(
                apply_server_side_encryption_by_default=aws.s3.BucketServerSideEncryptionConfigurationRuleApplyServerSideEncryptionByDefaultArgs(
                    sse_algorithm="aws:kms",
                    kms_master_key_id=kms_key.arn,
                ),
                bucket_key_enabled=True,
            )
        ],
    )
    
    # Block public access
    aws.s3.BucketPublicAccessBlock(
        "contact-records-public-access-block",
        bucket=log_bucket.id,
        block_public_acls=True,
        block_public_policy=True,
        ignore_public_acls=True,
        restrict_public_buckets=True,
    )
    
    # Require SSL/TLS for all requests
    log_bucket_ssl_policy = log_bucket.arn.apply(
        lambda arn: aws.iam.get_policy_document(
            statements=[
                aws.iam.GetPolicyDocumentStatementArgs(
                    sid="RequireSSL",
                    effect="Deny",
                    principals=[
                        aws.iam.GetPolicyDocumentStatementPrincipalArgs(
                            type="*",
                            identifiers=["*"],
                        )
                    ],
                    actions=["s3:*"],
                    resources=[
                        arn,
                        f"{arn}/*",
                    ],
                    conditions=[
                        aws.iam.GetPolicyDocumentStatementConditionArgs(
                            test="Bool",
                            variable="aws:SecureTransport",
                            values=["false"],
                        )
                    ],
                )
            ]
        ).json
    )
    
    aws.s3.BucketPolicy(
        "contact-records-ssl-policy",
        bucket=log_bucket.id,
        policy=log_bucket_ssl_policy,
    )
    
    # Get lifecycle configuration from Pulumi config
    config = pulumi.Config("s3")
    contact_records_archive_days = config.get_int("contactRecords.archiveDays") or config.get_int("archiveDays") or 90
    contact_records_deletion_days = config.get_int("contactRecords.deletionDays") or config.get_int("deletionDays") or 365
    
    # Add lifecycle policy
    aws.s3.BucketLifecycleConfiguration(
        "contact-records-lifecycle",
        bucket=log_bucket.id,
        rules=[
            aws.s3.BucketLifecycleConfigurationRuleArgs(
                id="archive-and-expire",
                status="Enabled",
                transitions=[
                    aws.s3.BucketLifecycleConfigurationRuleTransitionArgs(
                        days=contact_records_archive_days,
                        storage_class="STANDARD_IA",
                    ),
                ],
                expiration=aws.s3.BucketLifecycleConfigurationRuleExpirationArgs(
                    days=contact_records_deletion_days,
                ),
            )
        ],
    )
    
    # Enable server access logging
    aws.s3.BucketLogging(
        "contact-records-logging",
        bucket=log_bucket.id,
        target_bucket=logging_bucket.id,
        target_prefix="contact-records/",
    )
    
    # Create IAM role for Firehose
    firehose_assume_role_policy = aws.iam.get_policy_document(
        statements=[
            aws.iam.GetPolicyDocumentStatementArgs(
                actions=["sts:AssumeRole"],
                principals=[
                    aws.iam.GetPolicyDocumentStatementPrincipalArgs(
                        type="Service",
                        identifiers=["firehose.amazonaws.com"],
                    )
                ],
            )
        ]
    )
    
    firehose_role = aws.iam.Role(
        "firehose-role",
        assume_role_policy=firehose_assume_role_policy.json,
        tags=tags,
    )
    
    # Attach policy to allow S3 access - properly handle the Output
    firehose_policy = log_bucket.arn.apply(
        lambda bucket_arn: aws.iam.get_policy_document(
            statements=[
                aws.iam.GetPolicyDocumentStatementArgs(
                    actions=[
                        "s3:PutObject",
                        "s3:GetObject",
                        "s3:ListBucket",
                    ],
                    resources=[
                        f"{bucket_arn}/*",
                        bucket_arn,
                    ],
                )
            ]
        ).json
    )
    
    aws.iam.RolePolicy(
        "firehose-policy",
        role=firehose_role.id,
        policy=firehose_policy,
    )
    
    # Create Firehose delivery stream with explicit dependency and encryption
    firehose = aws.kinesis.FirehoseDeliveryStream(
        "contact-records",
        destination="extended_s3",
        extended_s3_configuration=aws.kinesis.FirehoseDeliveryStreamExtendedS3ConfigurationArgs(
            role_arn=firehose_role.arn,
            bucket_arn=log_bucket.arn,
            prefix="contact-records/",
            error_output_prefix="errors/",
            buffering_size=5,
            buffering_interval=300,
        ),
        server_side_encryption=aws.kinesis.FirehoseDeliveryStreamServerSideEncryptionArgs(
            enabled=True,
            key_type="CUSTOMER_MANAGED_CMK",
            key_arn=kms_key.arn,
        ),
        tags=tags,
        opts=pulumi.ResourceOptions(depends_on=[firehose_role, log_bucket, kms_key])
    )
    
    return firehose, log_bucket


def setup_analytics_data_lake(
    connect_instance: aws.connect.Instance,
    data_set_ids: Optional[List[str]] = None,
    tags: Dict[str, str] = None
) -> command.local.Command:
    """
    Associate Amazon Connect analytics data lake tables with the Connect instance.
    
    This uses the AWS CLI to call the batch-associate-analytics-data-set API,
    which is not yet available as a native Pulumi resource.
    
    Args:
        connect_instance: The Amazon Connect instance
        data_set_ids: List of data set IDs to associate. If None, uses all available tables.
        tags: Tags to apply (for metadata only, not directly applied to the association)
        
    Returns:
        The Command resource that executes the AWS CLI command
    """
    # Default to all available tables if not specified
    if data_set_ids is None:
        data_set_ids = [
            "contact_record",
            "contact_lens_conversational_analytics",
            "contact_statistic_record",
            "agent_queue_statistic_record",
            "agent_statistic_record",
            "contact_evaluation_record",
            "contact_flow_events",
            "bot_conversations",
            "bot_intents",
            "bot_slots",
            "routing_profiles",
            "users",
            "agent_hierarchy_groups",
            "staff_shifts",
            "shift_activities",
            "staff_timeoff_intervals",
            "staffing_group_forecast_groups",
            "staff_timeoff_balance_changes",
            "forecast_groups",
            "long_term_forecasts",
            "staff_shift_activities",
            "shift_profiles",
            "staffing_group_supervisors",
            "short_term_forecasts",
            "staffing_groups",
            "staff_timeoffs",
            "staff_scheduling_profile"
        ]
    
    # Get current AWS account ID
    current = aws.get_caller_identity()
    account_id = current.account_id
    
    # Build the JSON input structure
    input_data = pulumi.Output.all(
        instance_id=connect_instance.id,
        account_id=account_id
    ).apply(lambda args: json.dumps({
        "InstanceId": args["instance_id"],
        "DataSetIds": data_set_ids,
        "TargetAccountId": args["account_id"],
    }, indent=2))
    
    # Create the AWS CLI command that writes JSON to a temp file then uses it
    # This avoids shell escaping issues with nested quotes
    cli_command = input_data.apply(
        lambda json_input: (
            f"TMPFILE=$(mktemp) && "
            f"cat > $TMPFILE << 'EOF'\n{json_input}\nEOF\n"
            f"aws connect batch-associate-analytics-data-set --cli-input-json file://$TMPFILE && "
            f"rm -f $TMPFILE"
        )
    )
    
    # Create the command using Pulumi Command provider
    data_lake_setup = command.local.Command(
        "analytics-data-lake-setup",
        create=cli_command,
        # The delete command would disassociate the data sets
        # For now, we'll leave it empty as you typically don't want to remove this
        opts=pulumi.ResourceOptions(
            depends_on=[connect_instance],
            additional_secret_outputs=["stdout", "stderr"],
        ),
    )
    
    pulumi.export("analytics_data_lake_status", "configured")
    pulumi.export("analytics_data_lake_tables", data_set_ids)
    
    return data_lake_setup
