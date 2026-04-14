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
Voicemail Solution for Amazon Connect (elevai-vmail)

Architecture:
  Connect DISCONNECTED event
    → EventBridge rule (aws.connect)
    → SQS + DLQ
    → vmail-transcription Lambda   (trim WAV, upload, start Transcribe job, exit)

  Transcribe Job State Change: COMPLETED
    → EventBridge rule (aws.transcribe)
    → vmail-routing Lambda  (read raw output, write clean JSON envelope, create task/case)
"""

import json
import os
from typing import Dict, Optional

import pulumi
import pulumi_aws as aws
import pulumi_aws_native as aws_native
import pulumi_command as command

from core.utils import (
    create_secure_s3_bucket,
    create_sqs_queue_with_dlq,
    create_lambda_with_requirements,
    create_lambda_role,
)
from ..utils.naming import create_name, create_logical_name

# Base path to the lambda-code directory (two levels up from this file)
_LAMBDA_CODE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "lambda-code",
)

# Contact flow assets live alongside the IaC code, not in lambda-code
_CONTACT_FLOWS_DIR = os.path.join(
    os.path.dirname(__file__),
    "contact_flows",
)


def create_vmail_infrastructure(
    connect_instance: aws.connect.Instance,
    call_recordings_bucket: aws.s3.Bucket,
    tags: Dict[str, str],
    kms_key: aws.kms.Key,
    logging_bucket: aws.s3.Bucket,
    utils_lambda: Optional[aws.lambda_.Function] = None,
    cases_domain: Optional[Dict] = None,
    task_contact_flow_arn: Optional[pulumi.Output] = None,
    task_template_arn: Optional[pulumi.Output] = None,
    amplify_url: Optional[pulumi.Output] = None,
) -> Dict:
    """
    Create all infrastructure for the voicemail feature.

    Args:
        connect_instance: The Amazon Connect instance
        call_recordings_bucket: Existing S3 bucket holding IVR call recordings
        tags: Tags to apply to all resources
        kms_key: KMS key for encryption
        logging_bucket: S3 bucket for access logs
        utils_lambda: Optional utils Lambda function for contact flow module
        cases_domain: Optional Cases domain dict (from create_cases_domain)
        task_contact_flow_arn: Pre-created task contact flow ARN (Output), created
            externally after the utils Lambda so the ARN can be substituted into
            the flow JSON. Used by the task template.
        task_template_arn: Pre-created task template ARN (Output), passed in when
            the template is created externally (after the task flow ARN is known).

    Returns:
        Dictionary of created resources
    """
    vmail_tags = {**tags, "Feature": "elevai-vmail"}

    # ------------------------------------------------------------------ #
    # Shared storage                                                       #
    # ------------------------------------------------------------------ #
    vmail_bucket = _create_vmail_bucket(vmail_tags, kms_key, logging_bucket, amplify_url=amplify_url)

    # Transcribe permission to use the KMS key is granted via the key policy
    # in core/kms.py (Transcribe service principal in policy statement).
    # KMS grants do not support service principals as grantees.

    # ------------------------------------------------------------------ #
    # Processor Lambda  (Connect event → trim WAV → start Transcribe)    #
    # ------------------------------------------------------------------ #
    queues = create_sqs_queue_with_dlq(
        purpose="vmail",
        tags=vmail_tags,
        kms_key=kms_key,
        delay_seconds=10,
        visibility_timeout_seconds=120,
        message_retention_seconds=345600,   # 4 days
        dlq_retention_seconds=1209600,      # 14 days
        max_receive_count=3,
    )
    main_queue = queues["main_queue"]
    dlq = queues["dlq"]

    transcription_role_proc, _ = _create_processor_role(
        call_recordings_bucket=call_recordings_bucket,
        vmail_bucket=vmail_bucket,
        main_queue=main_queue,
        tags=vmail_tags,
        kms_key=kms_key,
    )

    processor_lambda = create_lambda_with_requirements(
        purpose="vmail-transcription",
        lambda_dir=os.path.join(_LAMBDA_CODE_DIR, "vmail-transcription"),
        iam_role=transcription_role_proc,
        tags=vmail_tags,
        memory_size=512,
        timeout=120,
        environment_variables={
            "RECORDINGS_BUCKET": call_recordings_bucket.id,
            "VMAIL_BUCKET": vmail_bucket.id,
            "RECORDINGS_PREFIX": "call-recordings/ivr",
            # Set TRANSCRIBE_AUTO_DETECT_LANGUAGE=true to enable automatic language
            # identification. When enabled, TRANSCRIBE_LANGUAGE_CODE is ignored.
            # Optionally set TRANSCRIBE_LANGUAGE_OPTIONS to a comma-separated list
            # of BCP-47 codes (e.g. "en-GB,en-US,fr-FR") to narrow detection.
            "TRANSCRIBE_AUTO_DETECT_LANGUAGE": "false",
            "TRANSCRIBE_LANGUAGE_CODE": "en-GB",
            "TRANSCRIBE_LANGUAGE_OPTIONS": "",
        },
    )

    stage = pulumi.get_stack()

    aws.lambda_.EventSourceMapping(
        f"{stage}-lbd-vmail-transcription-sqs-mapping",
        event_source_arn=main_queue.arn,
        function_name=processor_lambda.name,
        batch_size=1,
        function_response_types=["ReportBatchItemFailures"],
        opts=pulumi.ResourceOptions(depends_on=[processor_lambda, main_queue]),
    )

    _attach_sqs_eventbridge_policy(main_queue, purpose="transcription")
    _create_connect_eventbridge_rule(main_queue, vmail_tags)

    # ------------------------------------------------------------------ #
    # View + Guide (step-by-step guide for agent workspace)              #
    # ------------------------------------------------------------------ #
    vmail_view = None
    guide_flow = None
    if utils_lambda is not None:
        vmail_view = _create_vmail_view(
            connect_instance=connect_instance,
            tags=vmail_tags,
        )
        guide_flow = _create_guide_contact_flow(
            connect_instance=connect_instance,
            utils_lambda=utils_lambda,
            vmail_view=vmail_view,
            tags=vmail_tags,
        )

    # ------------------------------------------------------------------ #
    # Task Contact Flow + Template                                         #
    # ------------------------------------------------------------------ #
    # The task flow is created externally in __init__.py (after the utils
    # Lambda) so the Lambda ARN can be substituted into the flow JSON.
    # task_contact_flow_arn is that externally-created flow's ARN passed in
    # as a Pulumi Output. If not provided, fall back to creating the flow
    # here — but only when utils_lambda is available so placeholders can be
    # substituted (mirrors the module's guard in _create_vmail_contact_flow).
    if task_contact_flow_arn is None:
        internal_flow, _ = _create_task_contact_flow(
            connect_instance=connect_instance,
            tags=vmail_tags,
            guide_flow=guide_flow,
        )
        task_contact_flow_arn = internal_flow.contact_flow_arn

    task_template = None
    if task_contact_flow_arn is not None:
        task_template = _create_task_template(
            connect_instance=connect_instance,
            task_contact_flow_arn=task_contact_flow_arn,
            tags=vmail_tags,
        )

    # ------------------------------------------------------------------ #
    # Case Template (optional - create before transcription Lambda)      #
    # ------------------------------------------------------------------ #
    case_template = None
    
    # Create case template if Cases domain is available
    if cases_domain:
        case_template = _create_vmail_case_template(
            cases_domain=cases_domain["domain"],
            tags=vmail_tags,
        )

    # ------------------------------------------------------------------ #
    # Transcription Lambda  (Transcribe COMPLETED → write JSON envelope)  #
    # ------------------------------------------------------------------ #
    transcription_queues = create_sqs_queue_with_dlq(
        purpose="vmail-routing",
        tags=vmail_tags,
        kms_key=kms_key,
        visibility_timeout_seconds=120,   # 2× Lambda timeout (60s)
        message_retention_seconds=345600, # 4 days
        dlq_retention_seconds=1209600,    # 14 days
        max_receive_count=3,
    )
    transcription_queue = transcription_queues["main_queue"]
    transcription_dlq = transcription_queues["dlq"]

    routing_role, _ = _create_transcription_role(
        connect_instance=connect_instance,
        vmail_bucket=vmail_bucket,
        transcription_queue=transcription_queue,
        tags=vmail_tags,
        kms_key=kms_key,
        cases_domain=cases_domain,
    )

    _attach_sqs_eventbridge_policy(transcription_queue, purpose="routing")
    _create_transcribe_eventbridge_rule(transcription_queue, vmail_tags)

    # routing Lambda is created separately via create_vmail_routing_lambda()
    # after the task template ARN is known (task flow → task template → routing Lambda).
    routing_lambda = None

    # ------------------------------------------------------------------ #
    # Contact flow module                                                  #
    # ------------------------------------------------------------------ #
    contact_flow = None
    task_contact_flow = None
    vmail_sample_flow = None
    if utils_lambda is not None:
        beep_prompt = _create_beep_prompt(
            connect_instance=connect_instance,
            vmail_bucket=vmail_bucket,
            tags=vmail_tags,
        )
        contact_flow = _create_vmail_contact_flow(
            connect_instance=connect_instance,
            utils_lambda=utils_lambda,
            beep_prompt=beep_prompt,
            tags=vmail_tags,
        )

        # Create standalone vmail sample flow
        vmail_sample_flow = _create_vmail_sample_flow(
            connect_instance=connect_instance,
            vmail_module=contact_flow,
            tags=vmail_tags,
        )

    # ------------------------------------------------------------------ #
    # Exports                                                              #
    # ------------------------------------------------------------------ #
    pulumi.export("vmail_bucket_name", vmail_bucket.id)
    pulumi.export("vmail_bucket_arn", vmail_bucket.arn)
    pulumi.export("vmail_queue_url", main_queue.url)
    pulumi.export("vmail_dlq_url", dlq.url)
    pulumi.export("vmail_transcription_lambda_name", processor_lambda.name)
    pulumi.export("vmail_transcription_lambda_arn", processor_lambda.arn)
    pulumi.export("vmail_routing_lambda_name", routing_lambda.name if routing_lambda else None)
    pulumi.export("vmail_routing_lambda_arn", routing_lambda.arn if routing_lambda else None)
    pulumi.export("vmail_transcription_queue_url", transcription_queue.url)
    pulumi.export("vmail_transcription_dlq_url", transcription_dlq.url)
    pulumi.export("vmail_task_template_id", task_template.id if task_template is not None else None)
    pulumi.export("vmail_task_contact_flow_arn", task_contact_flow_arn)
    pulumi.export("vmail_view_arn", vmail_view.view_arn if vmail_view is not None else None)
    pulumi.export("vmail_guide_flow_arn", guide_flow.contact_flow_arn if guide_flow is not None else None)
    pulumi.export("vmail_sample_flow_arn", vmail_sample_flow.contact_flow_arn if vmail_sample_flow is not None else None)

    return {
        "vmail_bucket": vmail_bucket,
        "main_queue": main_queue,
        "dlq": dlq,
        "transcription_lambda": processor_lambda,
        "transcription_role": transcription_role_proc,
        "routing_lambda": routing_lambda,
        "routing_role": routing_role,
        "transcription_queue": transcription_queue,
        "transcription_dlq": transcription_dlq,
        "contact_flow": contact_flow,
        "task_contact_flow": task_contact_flow,
        "task_template": task_template,
        "case_template": case_template,
        "vmail_view": vmail_view,
        "guide_flow": guide_flow,
        "vmail_sample_flow": vmail_sample_flow,
    }


# ---------------------------------------------------------------------------
# Routing Lambda (public — created after task template is known)
# ---------------------------------------------------------------------------

def create_vmail_routing_lambda(
    connect_instance: aws.connect.Instance,
    vmail_bucket: aws.s3.Bucket,
    transcription_queue: aws.sqs.Queue,
    routing_role: aws.iam.Role,
    task_template: aws_native.connect.TaskTemplate,
    tags: Dict[str, str],
    cases_domain: Optional[Dict] = None,
    case_template: Optional[aws_native.cases.Template] = None,
    customer_profiles_domain: Optional[aws.customerprofiles.Domain] = None,
) -> aws.lambda_.Function:
    """
    Create the vmail-routing Lambda and wire it to the transcription SQS queue.

    Called after the task template exists so CONNECT_TASK_TEMPLATE_ID is known.
    """
    vmail_tags = {**tags, "Feature": "elevai-vmail"}
    stage = pulumi.get_stack()

    env = {
        "VMAIL_BUCKET": vmail_bucket.id,
        "CONNECT_INSTANCE_ID": connect_instance.id,
        "CONNECT_TASK_TEMPLATE_ID": task_template.arn.apply(
            lambda arn: arn.split("/task-template/")[-1]
        ),
    }

    if cases_domain:
        env["CASES_DOMAIN_ID"] = cases_domain["domain"].domain_id
        env["CONNECT_CASE_TEMPLATE_ID"] = (
            case_template.id.apply(
                lambda arn: arn.split("/template/")[-1] if "/template/" in arn else arn
            )
            if case_template else ""
        )
    else:
        env["CASES_DOMAIN_ID"] = ""
        env["CONNECT_CASE_TEMPLATE_ID"] = ""

    if customer_profiles_domain:
        env["CUSTOMER_PROFILES_DOMAIN_ARN"] = customer_profiles_domain.arn
    else:
        env["CUSTOMER_PROFILES_DOMAIN_ARN"] = ""

    routing_lambda = create_lambda_with_requirements(
        purpose="vmail-routing",
        lambda_dir=os.path.join(_LAMBDA_CODE_DIR, "vmail-routing"),
        iam_role=routing_role,
        tags=vmail_tags,
        memory_size=256,
        timeout=60,
        environment_variables=env,
    )

    aws.lambda_.EventSourceMapping(
        f"{stage}-lbd-vmail-routing-sqs-mapping",
        event_source_arn=transcription_queue.arn,
        function_name=routing_lambda.name,
        batch_size=1,
        function_response_types=["ReportBatchItemFailures"],
        opts=pulumi.ResourceOptions(depends_on=[routing_lambda, transcription_queue]),
    )

    pulumi.export("vmail_routing_lambda_name", routing_lambda.name)
    pulumi.export("vmail_routing_lambda_arn", routing_lambda.arn)

    return routing_lambda


# ---------------------------------------------------------------------------
# Contact flow
# ---------------------------------------------------------------------------

def _create_beep_prompt(
    connect_instance: aws.connect.Instance,
    vmail_bucket: aws.s3.Bucket,
    tags: Dict[str, str],
) -> aws_native.connect.Prompt:
    """
    Upload vmail-beep.wav to the vmail S3 bucket (unencrypted — Connect reads
    it directly as a service principal) and register it as a Connect prompt.
    """
    wav_path = os.path.join(_CONTACT_FLOWS_DIR, "vmail-beep.wav")
    stage = pulumi.get_stack()

    # Upload with no server-side encryption — Connect cannot use KMS-encrypted
    # S3 objects when reading prompts via the service principal.
    wav_object = aws.s3.BucketObject(
        f"{stage}-s3-vmail-beep-wav",
        bucket=vmail_bucket.id,
        key="prompts/vmail-beep.wav",
        source=pulumi.FileAsset(wav_path),
        content_type="audio/wav",
        server_side_encryption="AES256",  # S3-managed, not KMS
        tags=tags,
    )

    return aws_native.connect.Prompt(
        f"{stage}-connect-prompt-vmail-beep",
        instance_arn=connect_instance.arn,
        name="vmail-beep",
        description="Voicemail beep tone",
        s3_uri=pulumi.Output.concat("s3://", vmail_bucket.id, "/prompts/vmail-beep.wav"),
        tags=[aws_native.TagArgs(key=k, value=v) for k, v in tags.items()],
        opts=pulumi.ResourceOptions(depends_on=[wav_object]),
    )


def _create_vmail_contact_flow(
    connect_instance: aws.connect.Instance,
    utils_lambda: aws.lambda_.Function,
    beep_prompt: aws_native.connect.Prompt,
    tags: Dict[str, str],
) -> aws_native.connect.ContactFlowModule:
    """
    Deploy the elevai-vmail contact flow module, injecting the
    utils Lambda ARN and beep prompt ARN.

    Uses aws-native provider which supports the settings parameter properly.
    The Settings block (InputParameters/OutputParameters/Transitions) stays in content.
    The settings parameter is for the input schema that defines module parameters.
    """
    flow_path = os.path.join(_CONTACT_FLOWS_DIR, "elevai-vmail-module.json")
    with open(flow_path, "r") as f:
        flow_data = json.loads(f.read())

    stage = pulumi.get_stack()

    # Extract the input schema from Metadata.settings.input for the settings parameter
    input_schema = flow_data.get("Metadata", {}).get("settings", {}).get("input", {})
    settings_schema = json.dumps({"input": input_schema}) if input_schema else json.dumps({
        "input": {
            "schema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    })

    # The content includes the full flow JSON with Settings block
    flow_template = json.dumps(flow_data)
    content = pulumi.Output.all(
        utils_lambda.arn,
        utils_lambda.name,
        beep_prompt.prompt_arn,
    ).apply(lambda args: flow_template
        .replace("{{UTILS_LAMBDA_ARN}}", args[0])
        .replace("{{UTILS_LAMBDA_NAME}}", args[1])
        .replace("{{BEEP_PROMPT_ARN}}", args[2])
    )

    return aws_native.connect.ContactFlowModule(
        f"{stage}-cf-vmail",
        instance_arn=connect_instance.arn,
        name="Elevai Vmail",
        description="Voicemail capture module — records a message and tags the contact",
        content=content,
        settings=settings_schema,
        state="ACTIVE",
        tags=[aws_native.TagArgs(key=k, value=v) for k, v in {**tags, "Name": "Elevai Vmail"}.items()],
        opts=pulumi.ResourceOptions(
            depends_on=[beep_prompt],
        ),
    )


# ---------------------------------------------------------------------------
# View (step-by-step guide)
# ---------------------------------------------------------------------------

def _create_vmail_view(
    connect_instance: aws.connect.Instance,
    tags: Dict[str, str],
) -> aws_native.connect.View:
    """
    Create the Elevai-vmail view (step-by-step guide) that displays
    the voicemail transcript and embedded audio player.
    """
    stage = pulumi.get_stack()

    view_path = os.path.join(_CONTACT_FLOWS_DIR, "elevai-vmail-view.json")
    with open(view_path, "r") as f:
        view_data = json.loads(f.read())

    return aws_native.connect.View(
        f"{stage}-connect-view-vmail",
        instance_arn=connect_instance.arn,
        name="Elevai Vmail",
        description="Voicemail step-by-step guide with transcript and audio player",
        template=view_data["Template"],
        actions=[],
        tags=[aws_native.TagArgs(key=k, value=v) for k, v in {**tags, "Purpose": "Guide"}.items()],
    )


# ---------------------------------------------------------------------------
# Guide Contact Flow (event flow for agent workspace)
# ---------------------------------------------------------------------------

def _create_guide_contact_flow(
    connect_instance: aws.connect.Instance,
    utils_lambda: aws.lambda_.Function,
    vmail_view: aws_native.connect.View,
    tags: Dict[str, str],
) -> aws_native.connect.ContactFlow:
    """
    Create the elevai-vmail-guide contact flow that triggers the Lambda
    to get a presigned WAV URL and shows the voicemail view to the agent.

    Set as an event flow (AgentBeforeContactWork) on the task contact flow.
    """
    stage = pulumi.get_stack()

    flow_path = os.path.join(_CONTACT_FLOWS_DIR, "elevai-vmail-guide.json")
    with open(flow_path, "r") as f:
        flow_template = f.read()

    content = pulumi.Output.all(
        utils_lambda.arn,
        utils_lambda.name,
        vmail_view.view_arn,
    ).apply(lambda args: flow_template
        .replace("{{UTILS_LAMBDA_ARN}}", args[0])
        .replace("{{UTILS_LAMBDA_NAME}}", args[1])
        .replace("{{VMAIL_VIEW_ARN}}", f"{args[2]}:$LATEST")
    )

    return aws_native.connect.ContactFlow(
        f"{stage}-cf-vmail-guide",
        instance_arn=connect_instance.arn,
        name="Elevai Vmail Guide",
        description="Displays the voicemail transcript and audio player",
        type="CONTACT_FLOW",
        content=content,
        state="ACTIVE",
        tags=[aws_native.TagArgs(key=k, value=v) for k, v in {**tags, "Name": "Elevai Vmail Guide"}.items()],
        opts=pulumi.ResourceOptions(depends_on=[vmail_view]),
    )


# ---------------------------------------------------------------------------
# Vmail Sample Contact Flow
# ---------------------------------------------------------------------------

def _create_vmail_sample_flow(
    connect_instance: aws.connect.Instance,
    vmail_module: aws_native.connect.ContactFlowModule,
    tags: Dict[str, str],
) -> aws_native.connect.ContactFlow:
    """
    Create the Elevai Sample Vmail contact flow.

    A standalone sample flow that invokes the vmail module with demo
    parameters. Can be assigned to a phone number directly.

    Automatically looks up the "BasicQueue" ARN from the Connect instance
    to pre-populate the queue input for the vmail module.
    """
    stage = pulumi.get_stack()

    flow_path = os.path.join(_CONTACT_FLOWS_DIR, "elevai-sample-vmail.json")
    with open(flow_path, "r") as f:
        flow_template = f.read()

    # Look up the "BasicQueue" ARN at deploy time via a Command resource.
    # Every Connect instance has this queue by default.
    basic_queue_lookup = command.local.Command(
        f"{stage}-lookup-basic-queue",
        create=connect_instance.id.apply(
            lambda iid: (
                f"aws connect list-queues --instance-id {iid}"
                f" --queue-types STANDARD"
                f" --query \"QueueSummaryList[?Name=='BasicQueue'].Arn | [0]\""
                f" --output text"
            )
        ),
        opts=pulumi.ResourceOptions(depends_on=[connect_instance]),
    )
    basic_queue_arn = basic_queue_lookup.stdout.apply(lambda s: s.strip())

    content = pulumi.Output.all(
        vmail_module.contact_flow_module_arn,
        basic_queue_arn,
    ).apply(lambda args: flow_template
        .replace("{{VMAIL_MODULE_ID}}", f"{args[0].split('/')[-1]}:$LATEST")
        .replace("{{SAMPLE_QUEUE_ARN}}", args[1])
    )

    return aws_native.connect.ContactFlow(
        f"{stage}-cf-elevai-sample-vmail",
        instance_arn=connect_instance.arn,
        name="Elevai Sample Vmail",
        description="Elevai sample flow for voicemail demo",
        type="CONTACT_FLOW",
        content=content,
        state="ACTIVE",
        tags=[aws_native.TagArgs(key=k, value=v) for k, v in {**tags, "Name": "Elevai Sample Vmail"}.items()],
        opts=pulumi.ResourceOptions(depends_on=[vmail_module]),
    )


# ---------------------------------------------------------------------------
# Task Template
# ---------------------------------------------------------------------------

def _create_task_template(
    connect_instance: aws.connect.Instance,
    task_contact_flow_arn: pulumi.Output,
    tags: Dict[str, str],
) -> aws_native.connect.TaskTemplate:
    """
    Create the 'elevai-vmail' task template.

    Fields surfaced to agents in the CCP:
      - CallerNumber  (read-only, pre-populated by Lambda)
    """
    stage = pulumi.get_stack()
    return aws_native.connect.TaskTemplate(
        f"{stage}-connect-vmail-task-template",
        instance_arn=connect_instance.arn,
        name="elevai-vmail",
        description="Voicemail task — review recording and transcript, then action or close.",
        contact_flow_arn=task_contact_flow_arn,
        fields=[
            aws_native.connect.TaskTemplateFieldArgs(
                id=aws_native.connect.TaskTemplateFieldIdentifierArgs(name="Task name"),
                type=aws_native.connect.TaskTemplateFieldType.NAME,
                description="The name of the voicemail task.",
            ),
            aws_native.connect.TaskTemplateFieldArgs(
                id=aws_native.connect.TaskTemplateFieldIdentifierArgs(name="Summary"),
                type=aws_native.connect.TaskTemplateFieldType.TEXT_AREA,
                description="AI-generated summary of the voicemail.",
            ),
            aws_native.connect.TaskTemplateFieldArgs(
                id=aws_native.connect.TaskTemplateFieldIdentifierArgs(name="Transcript"),
                type=aws_native.connect.TaskTemplateFieldType.TEXT_AREA,
                description="AI-generated summary of the voicemail.",
            ),

            aws_native.connect.TaskTemplateFieldArgs(
                id=aws_native.connect.TaskTemplateFieldIdentifierArgs(name="Notes"),
                type=aws_native.connect.TaskTemplateFieldType.TEXT_AREA,
                description="Add notes to the task",
            ),
            aws_native.connect.TaskTemplateFieldArgs(
                id=aws_native.connect.TaskTemplateFieldIdentifierArgs(name="AssignedUser"),
                type=aws_native.connect.TaskTemplateFieldType.TEXT,
                description="User this voicemail is assigned to.",
            ),
            aws_native.connect.TaskTemplateFieldArgs(
                id=aws_native.connect.TaskTemplateFieldIdentifierArgs(name="AssignedQueue"),
                type=aws_native.connect.TaskTemplateFieldType.TEXT,
                description="Queue this voicemail is assigned to.",
            ),
        ],
        constraints=aws_native.connect.ConstraintsPropertiesArgs(
            read_only_fields=[
                aws_native.connect.TaskTemplateRequiredFieldInfoArgs(
                    id=aws_native.connect.TaskTemplateFieldIdentifierArgs(name="Task name"),
                ),
                aws_native.connect.TaskTemplateRequiredFieldInfoArgs(
                    id=aws_native.connect.TaskTemplateFieldIdentifierArgs(name="Summary"),
                ),
                aws_native.connect.TaskTemplateRequiredFieldInfoArgs(
                    id=aws_native.connect.TaskTemplateFieldIdentifierArgs(name="Transcript"),
                ),
                aws_native.connect.TaskTemplateRequiredFieldInfoArgs(
                    id=aws_native.connect.TaskTemplateFieldIdentifierArgs(name="AssignedUser"),
                ),
                aws_native.connect.TaskTemplateRequiredFieldInfoArgs(
                    id=aws_native.connect.TaskTemplateFieldIdentifierArgs(name="AssignedQueue"),
                ),
            ],
            required_fields=[
                aws_native.connect.TaskTemplateRequiredFieldInfoArgs(
                    id=aws_native.connect.TaskTemplateFieldIdentifierArgs(name="Task name"),
                ),
            ],
        ),
        defaults=[
            aws_native.connect.TaskTemplateDefaultFieldValueArgs(
                id=aws_native.connect.TaskTemplateFieldIdentifierArgs(name="Task name"),
                default_value="Voicemail"                
            )
        ],
        status=aws_native.connect.TaskTemplateStatus.ACTIVE,
        tags=[aws_native.TagArgs(key=k, value=v) for k, v in tags.items()]
    )


# ---------------------------------------------------------------------------
# Task Contact Flow
# ---------------------------------------------------------------------------

def _create_task_contact_flow(
    connect_instance: aws.connect.Instance,
    tags: Dict[str, str],
    guide_flow: Optional[aws_native.connect.ContactFlow] = None,
) -> tuple:
    """
    Create the task contact flow for voicemail tasks.

    Sets the target queue, configures the guide flow as the DefaultAgentUI
    event hook (step-by-step guide), then transfers the task to the queue.

    Returns (contact_flow_resource, contact_flow_id_output)
    where contact_flow_id_output is a Pulumi Output[str] suitable for use
    as an environment variable.
    """
    stage = pulumi.get_stack()

    flow_path = os.path.join(_CONTACT_FLOWS_DIR, "elevai-vmail-task.json")
    with open(flow_path, "r") as f:
        flow_template = f.read()

    if guide_flow is not None:
        content = guide_flow.contact_flow_arn.apply(
            lambda arn: flow_template.replace("{{VMAIL_GUIDE_FLOW_ARN}}", arn)
        )
    else:
        content = pulumi.Output.from_input(flow_template)

    depends = [r for r in [guide_flow] if r is not None]

    # Use aws-native provider which goes through CloudFormation
    cf = aws_native.connect.ContactFlow(
        f"{stage}-cf-vmail-task",
        instance_arn=connect_instance.arn,
        name="Elevai Vmail Task",
        description="Task contact flow for voicemail tasks.",
        type="CONTACT_FLOW",
        content=content,
        state="ACTIVE",
        tags=[aws_native.TagArgs(key=k, value=v) for k, v in {**tags, "Name": "Elevai Vmail Task"}.items()],
        opts=pulumi.ResourceOptions(depends_on=depends) if depends else None,
    )

    return cf, cf.contact_flow_arn.apply(lambda arn: arn.split("/")[-1])


# ---------------------------------------------------------------------------
# Case Template
# ---------------------------------------------------------------------------

def _create_vmail_case_template(
    cases_domain: aws_native.cases.Domain,
    tags: Dict[str, str],
) -> aws_native.cases.Template:
    """
    Create a case template for voicemail cases, with a layout that surfaces
    the built-in summary field in the case view.
    """
    stage = pulumi.get_stack()

    layout = aws_native.cases.Layout(
        f"{stage}-cases-vmail-layout",
        domain_id=cases_domain.domain_id,
        name="elevai-vmail",
        content=aws_native.cases.LayoutContentPropertiesArgs(
            basic=aws_native.cases.LayoutBasicLayoutArgs(
                more_info=aws_native.cases.LayoutSectionsArgs(
                    sections=[
                        aws_native.cases.LayoutSectionPropertiesArgs(
                            field_group=aws_native.cases.LayoutFieldGroupArgs(
                                name="Voicemail details",
                                fields=[],
                            )
                        )
                    ]
                ),
                top_panel=aws_native.cases.LayoutSectionsArgs(
                    sections=[
                        aws_native.cases.LayoutSectionPropertiesArgs(
                            field_group=aws_native.cases.LayoutFieldGroupArgs(
                                name="Fields",
                                fields=[
                                    aws_native.cases.LayoutFieldItemArgs(id="customer_id"),
                                    aws_native.cases.LayoutFieldItemArgs(id="summary"),
                                    aws_native.cases.LayoutFieldItemArgs(id="assigned_user"),
                                    aws_native.cases.LayoutFieldItemArgs(id="assigned_queue"),
                                ],
                            )
                        )
                    ]
                ),
            )
        ),
        opts=pulumi.ResourceOptions(depends_on=[cases_domain]),
    )

    return aws_native.cases.Template(
        f"{stage}-cases-vmail-template",
        domain_id=cases_domain.domain_id,
        name="elevai-vmail",
        description="Voicemail case template — review recording and transcript",
        required_fields=[
            aws_native.cases.TemplateRequiredFieldArgs(field_id="customer_id"),
            aws_native.cases.TemplateRequiredFieldArgs(field_id="title"),
        ],
        layout_configuration=aws_native.cases.TemplateLayoutConfigurationArgs(
            default_layout=layout.layout_id,
        ),
        status=aws_native.cases.TemplateStatus.ACTIVE,
        tags=[aws_native.TagArgs(key=k, value=v) for k, v in tags.items()],
        opts=pulumi.ResourceOptions(depends_on=[cases_domain, layout]),
    )


# ---------------------------------------------------------------------------
# S3
# ---------------------------------------------------------------------------

def _create_vmail_bucket(
    tags: Dict[str, str],
    kms_key: aws.kms.Key,
    logging_bucket: aws.s3.Bucket,
    amplify_url: Optional[pulumi.Output] = None,
) -> aws.s3.Bucket:
    # Transcribe accesses S3 directly as its own service principal — it does not
    # assume the Lambda role — so we must explicitly allow it in the bucket policy.
    # The StringEquals SourceAccount condition is not used here because account_id
    # is an Output; instead we scope by the Transcribe service principal and bucket
    # ARN (applied inside build_policy in create_secure_s3_bucket).
    transcribe_statements = [
        {
            "Sid": "AllowTranscribeObjects",
            "Effect": "Allow",
            "Principal": {"Service": "transcribe.amazonaws.com"},
            "Action": ["s3:GetObject", "s3:PutObject"],
            "Resource": "arn:aws:s3:::*/*",
        },
        {
            "Sid": "AllowTranscribeListBucket",
            "Effect": "Allow",
            "Principal": {"Service": "transcribe.amazonaws.com"},
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:s3:::*",
        },
    ]

    bucket = create_secure_s3_bucket(
        resource_name=create_logical_name("s3", "vmail"),
        purpose="VoicemailRecordings",
        tags=tags,
        kms_key=kms_key,
        logging_bucket=logging_bucket,
        archive_days=90,
        deletion_days=365,
        additional_policy_statements=transcribe_statements,
        # Object Lock must be disabled — Amazon Transcribe cannot read from
        # buckets with Object Lock enabled (AWS service limitation).
        enable_object_lock=False,
    )

    # CORS — allow the Amplify app to fetch presigned URLs directly from the browser
    allowed_origins = pulumi.Output.from_input(
        amplify_url if amplify_url is not None else pulumi.Output.from_input("*")
    ).apply(lambda url: [url] if url != "*" else ["*"])

    aws.s3.BucketCorsConfiguration(
        create_logical_name("s3", "vmail-cors"),
        bucket=bucket.id,
        cors_rules=allowed_origins.apply(lambda origins: [
            aws.s3.BucketCorsConfigurationCorsRuleArgs(
                allowed_headers=["*"],
                allowed_methods=["GET"],
                allowed_origins=origins,
                expose_headers=["ETag"],
                max_age_seconds=3600,
            )
        ]),
    )

    return bucket


# ---------------------------------------------------------------------------
# IAM – processor Lambda
# ---------------------------------------------------------------------------

def _create_processor_role(
    call_recordings_bucket: aws.s3.Bucket,
    vmail_bucket: aws.s3.Bucket,
    main_queue: aws.sqs.Queue,
    tags: Dict[str, str],
    kms_key: aws.kms.Key,
) -> tuple:
    """
    Least-privilege role for the processor Lambda:
    - Read source recordings from the call-recordings bucket
    - Write trimmed WAV to the vmail bucket
    - Consume messages from the SQS queue
    - KMS decrypt / generate data key
    - Start Transcribe jobs and tag them
    """
    policy_statements = pulumi.Output.all(
        call_recordings_bucket.arn,
        vmail_bucket.arn,
        main_queue.arn,
        kms_key.arn,
    ).apply(lambda args: [
        {
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:HeadObject", "s3:ListBucket"],
            "Resource": [args[0], f"{args[0]}/*"],
        },
        {
            "Effect": "Allow",
            "Action": ["s3:PutObject", "s3:GetObject", "s3:HeadObject"],
            "Resource": f"{args[1]}/*",
        },
        {
            "Effect": "Allow",
            "Action": [
                "sqs:ReceiveMessage",
                "sqs:DeleteMessage",
                "sqs:GetQueueAttributes",
                "sqs:ChangeMessageVisibility",
            ],
            "Resource": args[2],
        },
        {
            "Effect": "Allow",
            "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
            "Resource": args[3],
        },
        {
            "Effect": "Allow",
            "Action": ["connect:GetContactAttributes"],
            "Resource": "*",
        },
        {
            "Effect": "Allow",
            "Action": [
                "transcribe:StartTranscriptionJob",
                "transcribe:TagResource",
            ],
            "Resource": "*",
        },
    ])

    return create_lambda_role(
        purpose="vmail-transcription",
        tags=tags,
        additional_policy_statements=policy_statements,
    )


# ---------------------------------------------------------------------------
# IAM – routing Lambda
# ---------------------------------------------------------------------------

def _create_transcription_role(
    connect_instance: aws.connect.Instance,
    vmail_bucket: aws.s3.Bucket,
    transcription_queue: aws.sqs.Queue,
    tags: Dict[str, str],
    kms_key: aws.kms.Key,
    cases_domain: Optional[Dict] = None,
) -> tuple:
    """
    Least-privilege role for the transcription Lambda:
    - Read raw Transcribe output and write clean JSON envelope in vmail bucket
    - Delete the intermediate Transcribe-named file
    - Fetch Transcribe job metadata (for tags / language code)
    - KMS decrypt / generate data key
    - Consume messages from the transcription SQS queue
    - Create Connect task contacts and use task templates
    - Create Cases and attach files (if Cases is enabled)
    - Create Cases and attach files (if Cases is enabled)
    """
    base_statements = pulumi.Output.all(
        vmail_bucket.arn,
        kms_key.arn,
        connect_instance.arn,
        transcription_queue.arn,
    ).apply(lambda args: [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
            ],
            "Resource": f"{args[0]}/*",
        },
        {
            "Effect": "Allow",
            "Action": ["s3:ListBucket"],
            "Resource": args[0],
        },
        {
            "Effect": "Allow",
            "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
            "Resource": args[1],
        },
        {
            "Effect": "Allow",
            "Action": ["transcribe:GetTranscriptionJob"],
            "Resource": "*",
        },
        {
            "Effect": "Allow",
            "Action": ["connect:StartTaskContact"],
            "Resource": [
                f"{args[2]}/task-template/*",
                f"{args[2]}/contact/*",
                f"{args[2]}/contact-flow/*",
            ],
        },
        {
            "Effect": "Allow",
            "Action": ["connect:StartAttachedFileUpload", "connect:CompleteAttachedFileUpload"],
            # When AssociatedResourceArn is a Cases case ARN, AWS evaluates the
            # permission against the Cases resource, not the Connect instance.
            "Resource": "*",
        },
        {
            "Effect": "Allow",
            "Action": [
                "sqs:ReceiveMessage",
                "sqs:DeleteMessage",
                "sqs:GetQueueAttributes",
                "sqs:ChangeMessageVisibility",
            ],
            "Resource": args[3],
        },
        {
            "Effect": "Allow",
            "Action": ["bedrock:InvokeModel"],
            "Resource": "arn:aws:bedrock:*::foundation-model/amazon.nova-pro-v1:0",
        },
    ])

    # Cases permissions are determined at Python evaluation time (not inside .apply)
    # so the statement is always included when cases_domain is provided, regardless
    # of whether the domain ARN resolves to a non-empty string at deploy time.
    if cases_domain:
        cases_statement = pulumi.Output.from_input([{
            "Effect": "Allow",
            "Action": [
                "cases:CreateCase",
                "cases:GetCase",
                "cases:UpdateCase",
                "cases:CreateRelatedItem",
                "cases:GetDomain"
            ],
            # Cases API does not support resource-level permissions for CreateCase;
            # wildcard is required.
            "Resource": "*",
        }, {
            "Effect": "Allow",
            # CreateCase internally calls profile:SearchProfiles to validate the
            # customer_id ARN. Without this the Cases service returns AccessDeniedException.
            "Action": ["profile:SearchProfiles"],
            "Resource": "*",
        }, {
            "Effect": "Allow",
            # CreateRelatedItem with type=Contact requires connect:DescribeContact
            # Assigning case to users and queue connect:DescribeQueue and connect:DescribeUser
            # permission on the contact ARN being associated with the case.
            "Action": [
                "connect:DescribeContact", 
                "connect:ListInstances", 
                "connect:ListIntegrationAssociations", 
                "ds:DescribeDirectories", 
                "connect:DescribeQueue", 
                "connect:DescribeUser"
            ],
            "Resource": "*",
        }])
        policy_statements = pulumi.Output.all(base_statements, cases_statement).apply(
            lambda args: args[0] + args[1]
        )
    else:
        policy_statements = base_statements

    return create_lambda_role(
        purpose="vmail-routing",
        tags=tags,
        additional_policy_statements=policy_statements,
    )


# ---------------------------------------------------------------------------
# KMS grant for Transcribe
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# EventBridge – Connect DISCONNECTED → SQS
# ---------------------------------------------------------------------------

def _attach_sqs_eventbridge_policy(queue: aws.sqs.Queue, purpose: str = "processor") -> None:
    """Allow EventBridge to send messages to an SQS queue."""
    region = aws.get_region()
    account = aws.get_caller_identity()

    policy = pulumi.Output.all(queue.arn, region.id, account.account_id).apply(
        lambda args: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Sid": "AllowEventBridgeSendMessage",
                "Effect": "Allow",
                "Principal": {"Service": "events.amazonaws.com"},
                "Action": "sqs:SendMessage",
                "Resource": args[0],
                "Condition": {
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:events:{args[1]}:{args[2]}:rule/*"
                    }
                },
            }],
        })
    )

    stage = pulumi.get_stack()
    aws.sqs.QueuePolicy(
        f"{stage}-sqs-vmail-{purpose}-eventbridge-policy",
        queue_url=queue.url,
        policy=policy,
    )


def _create_connect_eventbridge_rule(
    target_queue: aws.sqs.Queue,
    tags: Dict[str, str],
) -> aws.cloudwatch.EventRule:
    """EventBridge rule: Connect DISCONNECTED + elevai-vmail=true → SQS."""
    rule_name = create_name("eb", "vmail-disconnected")
    rule_logical = create_logical_name("eb", "vmail-disconnected")

    rule = aws.cloudwatch.EventRule(
        rule_logical,
        name=rule_name,
        description="Capture Amazon Connect DISCONNECTED events tagged for voicemail",
        event_pattern=json.dumps({
            "source": ["aws.connect"],
            "detail-type": ["Amazon Connect Contact Event"],
            "detail": {
                "eventType": ["DISCONNECTED"],
                "tags": {"elevai-vmail": ["true"]},
            },
        }),
        state="ENABLED",
        tags={**tags, "Name": rule_name},
    )

    aws.cloudwatch.EventTarget(
        create_logical_name("eb", "vmail-sqs-target"),
        rule=rule.name,
        arn=target_queue.arn,
    )

    return rule


# ---------------------------------------------------------------------------
# EventBridge – Transcribe COMPLETED → transcription Lambda
# ---------------------------------------------------------------------------

def _create_transcribe_eventbridge_rule(
    target_queue: aws.sqs.Queue,
    tags: Dict[str, str],
) -> aws.cloudwatch.EventRule:
    """EventBridge rule: Transcribe job COMPLETED, name prefix vmail- → SQS."""
    rule_name = create_name("eb", "vmail-transcribe-done")
    rule_logical = create_logical_name("eb", "vmail-transcribe-done")

    rule = aws.cloudwatch.EventRule(
        rule_logical,
        name=rule_name,
        description="Capture Transcribe COMPLETED events for vmail- jobs",
        event_pattern=json.dumps({
            "source": ["aws.transcribe"],
            "detail-type": ["Transcribe Job State Change"],
            "detail": {
                "TranscriptionJobStatus": ["COMPLETED"],
                "TranscriptionJobName": [{"prefix": "vmail-"}],
            },
        }),
        state="ENABLED",
        tags={**tags, "Name": rule_name},
    )

    aws.cloudwatch.EventTarget(
        create_logical_name("eb", "vmail-transcription-target"),
        rule=rule.name,
        arn=target_queue.arn,
    )

    return rule
