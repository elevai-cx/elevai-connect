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
Voicemail Transcription Result Lambda (elevai-connect-vmail)

Triggered by EventBridge rule:
  source: aws.transcribe
  detail-type: Transcribe Job State Change
  detail.TranscriptionJobStatus: COMPLETED
  detail.TranscriptionJobName: prefix "vmail-"

What it does:
1. Retrieves the completed Transcribe job to get full result metadata and tags.
2. Reads the raw Transcribe output JSON written directly to the vmail S3 bucket.
3. Writes a clean normalised envelope to:
     voicemails/<YYYY>/<MM>/<DD>/<contactId>.json
4. Deletes the intermediate raw file Transcribe wrote (named after the job).
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import boto3
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit

# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

logger = Logger(service=os.getenv("POWERTOOLS_SERVICE_NAME", "vmail-transcription"))
tracer = Tracer(service=os.getenv("POWERTOOLS_SERVICE_NAME", "vmail-transcription"))
metrics = Metrics(
    namespace=os.getenv("POWERTOOLS_METRICS_NAMESPACE", "AmazonConnect"),
    service=os.getenv("POWERTOOLS_SERVICE_NAME", "vmail-transcription"),
)

VMAIL_BUCKET = os.environ["VMAIL_BUCKET"]
CONNECT_INSTANCE_ID = os.environ["CONNECT_INSTANCE_ID"]
CONNECT_TASK_TEMPLATE_ID = os.environ["CONNECT_TASK_TEMPLATE_ID"]
CONNECT_CASE_TEMPLATE_ID = os.environ.get("CONNECT_CASE_TEMPLATE_ID", "")
CASES_DOMAIN_ID = os.environ.get("CASES_DOMAIN_ID", "")

s3 = boto3.client("s3")
transcribe = boto3.client("transcribe")
connect = boto3.client("connect")
connectcases = boto3.client("connectcases")
bedrock_runtime = boto3.client("bedrock-runtime")


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

@tracer.capture_lambda_handler
@logger.inject_lambda_context
@metrics.log_metrics
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """SQS batch handler — each record body contains an EventBridge Transcribe event."""
    records = event.get("Records", [])
    metrics.add_metric(name="TranscriptionResultInvocation", unit=MetricUnit.Count, value=1)
    metrics.add_metric(name="SQSRecordsReceived", unit=MetricUnit.Count, value=len(records))

    batch_item_failures = []

    for record in records:
        message_id = record.get("messageId")
        try:
            eb_event = json.loads(record.get("body", "{}"))
            detail = eb_event.get("detail", {})
            job_name: str = detail.get("TranscriptionJobName", "")
            job_status: str = detail.get("TranscriptionJobStatus", "")

            logger.info("Transcription result received", extra={"jobName": job_name, "status": job_status})

            if not job_name.startswith("vmail-"):
                logger.warning("Ignoring non-vmail job", extra={"jobName": job_name})
                continue

            if job_status != "COMPLETED":
                logger.warning("Job not COMPLETED – ignoring", extra={"jobName": job_name, "status": job_status})
                metrics.add_metric(name="TranscriptionResultIgnored", unit=MetricUnit.Count, value=1)
                continue

            _process_completed_job(job_name)

        except Exception as exc:
            logger.error(
                "Failed to process transcription record",
                extra={"messageId": message_id, "error": str(exc)},
            )
            metrics.add_metric(name="RecordFailed", unit=MetricUnit.Count, value=1)
            batch_item_failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": batch_item_failures}


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

@tracer.capture_method
def _generate_summary(transcript: str, custom_prompt: str = "") -> Optional[str]:
    """
    Generate a summary using Amazon Bedrock Nova Pro.
    
    Args:
        transcript: Full voicemail transcript text
        custom_prompt: Optional custom system prompt
        
    Returns:
        Summary text or None if generation fails or transcript is empty
    """
    if not transcript.strip():
        logger.warning("Empty transcript provided, skipping summary generation")
        return None
    
    system_prompt = custom_prompt or (
        "Summarize this voicemail transcript in 2-3 sentences, "
        "focusing on the caller's main request or message."
    )
    
    logger.info(
        "Invoking Bedrock for summary generation",
        extra={
            "modelId": "amazon.nova-pro-v1:0",
            "promptLength": len(system_prompt),
            "transcriptLength": len(transcript),
        },
    )
    
    start_time = time.time()
    
    try:
        response = bedrock_runtime.invoke_model(
            modelId="amazon.nova-pro-v1:0",
            body=json.dumps({
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": transcript}]
                    }
                ],
                "system": [{"text": system_prompt}],
                "inferenceConfig": {
                    "max_new_tokens": 200,
                    "temperature": 0.3
                }
            })
        )
        
        latency = time.time() - start_time
        
        result = json.loads(response["body"].read())
        summary = result["output"]["message"]["content"][0]["text"]
        summary_text = summary.strip()
        
        logger.info(
            "Bedrock summary generated successfully",
            extra={
                "summaryLength": len(summary_text),
                "latencySeconds": round(latency, 3),
            },
        )
        metrics.add_metric(name="BedrockSummaryGenerated", unit=MetricUnit.Count, value=1)
        metrics.add_metric(name="BedrockLatency", unit=MetricUnit.Milliseconds, value=int(latency * 1000))
        
        return summary_text
        
    except Exception as exc:
        latency = time.time() - start_time
        logger.error(
            "Bedrock summary generation failed",
            extra={
                "error": str(exc),
                "errorType": type(exc).__name__,
                "latencySeconds": round(latency, 3),
            },
        )
        metrics.add_metric(name="BedrockSummaryFailed", unit=MetricUnit.Count, value=1)
        return None


@tracer.capture_method
def _process_completed_job(job_name: str) -> None:
    """Fetch Transcribe job details, read raw output, write clean envelope."""

    response = transcribe.get_transcription_job(TranscriptionJobName=job_name)
    job = response["TranscriptionJob"]

    # contactId and wav_key were stored as Transcribe job tags by the processor Lambda
    tags: Dict[str, str] = {t["Key"]: t["Value"] for t in job.get("Tags", [])}
    contact_id: str = tags.get("elevai-contact-id", "")
    wav_key: str = tags.get("elevai-wav-key", "")

    if not contact_id or not wav_key:
        raise ValueError(f"Job {job_name} is missing elevai-contact-id or elevai-wav-key tags")

    # Transcribe writes its output named after the job (not the WAV file) into the
    # same directory prefix that the processor Lambda specified as OutputKey.
    directory = wav_key.rsplit("/", 1)[0]
    final_key = f"{directory}/{job_name}.json"

    logger.info("Reading Transcribe output", extra={"bucket": VMAIL_BUCKET, "key": final_key})

    try:
        final_obj = s3.get_object(Bucket=VMAIL_BUCKET, Key=final_key)
        raw_data = json.loads(final_obj["Body"].read().decode("utf-8"))
        logger.info("Read Transcribe output", extra={"key": final_key})
    except s3.exceptions.NoSuchKey:
        logger.error("Transcribe output file not found", extra={"key": final_key})
        raise ValueError(f"Transcribe output not found at {final_key}")
    
    # Check if this is already a processed envelope or raw Transcribe output
    if "transcribeJobName" in raw_data:
        # Already processed - extract transcript and continue to task/case creation
        logger.info("File already processed, continuing to task/case creation", extra={"key": final_key})
        full_text = raw_data.get("transcript", "")
        _create_connect_task(contact_id, wav_key, final_key, full_text)
        return
    
    # Process raw Transcribe output
    results = raw_data.get("results", {})
    full_text = " ".join(
        t.get("transcript", "") for t in results.get("transcripts", [])
    ).strip()

    envelope = {
        "contactId": contact_id,
        "transcribeJobName": job_name,
        "transcribedAt": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "languageCode": job.get("LanguageCode", ""),
        "transcript": full_text,
        "items": results.get("items", []),
        "raw": raw_data,
    }

    # ------------------------------------------------------------------
    # Read .metadata sidecar to check for GenAI configuration
    # ------------------------------------------------------------------
    metadata_key = wav_key.replace(".wav", ".metadata")
    genai_summary_enabled = False
    genai_custom_prompt = ""
    
    try:
        meta_obj = s3.get_object(Bucket=VMAIL_BUCKET, Key=metadata_key)
        metadata = json.loads(meta_obj["Body"].read().decode("utf-8"))
        
        # Extract GenAI configuration from metadata
        genai_summary_str = metadata.get("elevai-connect-vmail-genai-summary", "false")
        genai_summary_enabled = genai_summary_str.lower() == "true"
        genai_custom_prompt = metadata.get("elevai-connect-vmail-genai-prompt", "")
        
        logger.info(
            "GenAI configuration read from metadata",
            extra={
                "contactId": contact_id,
                "genaiEnabled": genai_summary_enabled,
                "customPromptProvided": bool(genai_custom_prompt),
            },
        )
    except Exception as exc:
        logger.warning(
            "Failed to read .metadata sidecar for GenAI config – skipping summary generation",
            extra={"bucket": VMAIL_BUCKET, "key": metadata_key, "error": str(exc)},
        )
    
    # ------------------------------------------------------------------
    # Generate GenAI summary if enabled
    # ------------------------------------------------------------------
    if genai_summary_enabled and full_text:
        summary = _generate_summary(full_text, genai_custom_prompt)
        if summary:
            envelope["genaiSummary"] = summary
            logger.info(
                "GenAI summary added to envelope",
                extra={"contactId": contact_id, "summaryLength": len(summary)},
            )

    # ------------------------------------------------------------------
    # Write updated envelope to S3 before task/case creation
    # ------------------------------------------------------------------
    s3.put_object(
        Bucket=VMAIL_BUCKET,
        Key=final_key,
        Body=json.dumps(envelope, ensure_ascii=False, indent=2).encode("utf-8"),
        ContentType="application/json",
    )

    logger.info(
        "Transcription envelope stored",
        extra={
            "contactId": contact_id,
            "bucket": VMAIL_BUCKET,
            "key": final_key,
            "transcriptLength": len(full_text),
            "hasGenaiSummary": "genaiSummary" in envelope,
        },
    )
    metrics.add_metric(name="TranscriptStored", unit=MetricUnit.Count, value=1)
    metrics.add_metric(name="TranscriptLength", unit=MetricUnit.Count, value=len(full_text))

    # ------------------------------------------------------------------
    # Read .metadata sidecar and create an Amazon Connect Task
    # ------------------------------------------------------------------
    _create_connect_task(contact_id, wav_key, final_key, full_text)


# ---------------------------------------------------------------------------
# Connect Task creation
# ---------------------------------------------------------------------------

def _create_connect_task(contact_id: str, wav_key: str, json_key: str, transcript: str) -> None:
    """
    Read the .metadata sidecar for this voicemail, then create an Amazon
    Connect Task routed to the queue ARN stored in that file.

    The task is created with:
      - Name: "Voicemail from <callerNumber>"
      - Description: first 512 chars of the transcript (Connect limit)
      - Attributes: contactId, s3WavKey, s3JsonKey, callerNumber, queueArn
      - QueueId: queueArn from .metadata (controls agent routing)
    """
    metadata_key = wav_key.replace(".wav", ".metadata")

    try:
        meta_obj = s3.get_object(Bucket=VMAIL_BUCKET, Key=metadata_key)
        metadata = json.loads(meta_obj["Body"].read().decode("utf-8"))
    except Exception as exc:
        logger.error(
            "Failed to read .metadata sidecar – task will not be created",
            extra={"bucket": VMAIL_BUCKET, "key": metadata_key, "error": str(exc)},
        )
        metrics.add_metric(name="TaskMetadataReadFailed", unit=MetricUnit.Count, value=1)
        return

    queue_arn: str = metadata.get("elevai-connect-vmail-queue-arn", "")
    caller_number: str = metadata.get("elevai-connect-vmail-caller-number", "unknown")
    destination_channel: str = metadata.get("elevai-connect-vmail-destination-channel", "task")
    case_template_id: str = metadata.get("elevai-connect-vmail-destination-case-template-id", "") or CONNECT_CASE_TEMPLATE_ID
    customer_id: str = metadata.get("elevai-connect-vmail-customer-id", "")
    account_id: str = metadata.get("accountId", "")
    region: str = metadata.get("region", "")

    if not queue_arn:
        logger.warning(
            "elevai-connect-vmail-queue-arn not found in .metadata – notification will not be created",
            extra={"contactId": contact_id},
        )
        metrics.add_metric(name="TaskSkippedNoQueue", unit=MetricUnit.Count, value=1)
        return

    if destination_channel == "task":
        _deliver_via_task(contact_id, wav_key, json_key, transcript, queue_arn, caller_number)
    elif destination_channel == "case":
        if not case_template_id or not CASES_DOMAIN_ID:
            logger.warning(
                "Case delivery requested but case template or domain not configured",
                extra={"contactId": contact_id, "caseTemplateId": case_template_id, "domainId": CASES_DOMAIN_ID},
            )
            metrics.add_metric(name="CaseSkippedNotConfigured", unit=MetricUnit.Count, value=1)
            return
        if not customer_id:
            logger.warning(
                "Case delivery requested but customer_id not provided",
                extra={"contactId": contact_id},
            )
            metrics.add_metric(name="CaseSkippedNoCustomerId", unit=MetricUnit.Count, value=1)
            return
        _deliver_via_case(contact_id, wav_key, json_key, transcript, caller_number, customer_id, case_template_id, account_id, region)
    else:
        logger.warning(
            "Unsupported destination channel – skipping delivery",
            extra={"contactId": contact_id, "destinationChannel": destination_channel},
        )
        metrics.add_metric(name="DeliveryChannelUnsupported", unit=MetricUnit.Count, value=1)


def _deliver_via_task(
    contact_id: str,
    wav_key: str,
    json_key: str,
    transcript: str,
    queue_arn: str,
    caller_number: str,
) -> None:
    """
    Create an Amazon Connect Task for the voicemail.

    Routing is handled by the task contact flow (TransferContactToQueue).
    The queueArn from .metadata is stored as a task attribute for reference.
    """
    # Task name matches the template default; CallerNumber surfaces the caller in the CCP.
    task_name = "Voicemail"

    # Enforce field-level character limits from the task template.
    MAX_SUMMARY_LENGTH = 512
    MAX_TRANSCRIPT_LENGTH = 4096

    transcript_field = (transcript[:MAX_TRANSCRIPT_LENGTH - 1] + "…") if len(transcript) > MAX_TRANSCRIPT_LENGTH else transcript

    task_attributes = {
        "contactId": contact_id,
        "CallerNumber": caller_number,
        "s3WavKey": f"s3://{VMAIL_BUCKET}/{wav_key}",
        "s3JsonKey": f"s3://{VMAIL_BUCKET}/{json_key}",
        "elevai-connect-vmail-queue-arn": queue_arn,
    }

    # References render as named values in the CCP task panel.
    task_references: Dict[str, Dict[str, str]] = {
        "Transcript": {"Value": transcript_field, "Type": "STRING"},
    }

    # Read genaiSummary from the envelope (already written to S3 by _process_completed_job).
    # Summary is a template field (TEXT); 512-char limit enforced.
    try:
        envelope_obj = s3.get_object(Bucket=VMAIL_BUCKET, Key=json_key)
        envelope = json.loads(envelope_obj["Body"].read().decode("utf-8"))

        if "genaiSummary" in envelope:
            raw_summary = envelope["genaiSummary"]
            summary = (raw_summary[:MAX_SUMMARY_LENGTH - 1] + "…") if len(raw_summary) > MAX_SUMMARY_LENGTH else raw_summary
            task_references["Summary"] = {"Value": summary, "Type": "STRING"}
            logger.info(
                "Adding GenAI summary to task references",
                extra={"contactId": contact_id, "summaryLength": len(summary), "truncated": len(raw_summary) > MAX_SUMMARY_LENGTH},
            )
        else:
            logger.debug(
                "No GenAI summary available, omitting Summary reference",
                extra={"contactId": contact_id},
            )
    except Exception as exc:
        logger.warning(
            "Failed to read envelope for GenAI summary – omitting Summary reference",
            extra={"bucket": VMAIL_BUCKET, "key": json_key, "error": str(exc)},
        )

    logger.info(
        "Creating Connect Task",
        extra={
            "contactId": contact_id,
            "taskName": task_name,
            "queueArn": queue_arn,
            "instanceId": CONNECT_INSTANCE_ID,
            "taskTemplateId": CONNECT_TASK_TEMPLATE_ID,
            "transcriptLength": len(transcript_field),
            "attributes": task_attributes,
        },
    )

    try:
        response = connect.start_task_contact(
            InstanceId=CONNECT_INSTANCE_ID,
            TaskTemplateId=CONNECT_TASK_TEMPLATE_ID,
            Name=task_name,
            Attributes=task_attributes,
            References=task_references,
        )
        task_id = response.get("ContactId", "")
        logger.info(
            "Connect Task created",
            extra={"taskContactId": task_id, "contactId": contact_id, "queueArn": queue_arn},
        )
        metrics.add_metric(name="TaskCreated", unit=MetricUnit.Count, value=1)
    except Exception as exc:
        logger.error(
            "Failed to create Connect Task",
            extra={"contactId": contact_id, "error": str(exc)},
        )
        metrics.add_metric(name="TaskCreationFailed", unit=MetricUnit.Count, value=1)
        raise



def _deliver_via_case(
    contact_id: str,
    wav_key: str,
    json_key: str,
    transcript: str,
    caller_number: str,
    customer_id: str,
    case_template_id: str,
    account_id: str,
    region: str,
) -> None:
    """
    Create an Amazon Connect Case for the voicemail and attach the WAV file.
    
    The case is created with:
      - Template: from metadata or default CONNECT_CASE_TEMPLATE_ID
      - Fields: customer_id (required), title (required), summary (with GenAI summary or fallback)
      - Attached file: The voicemail WAV file via Connect StartAttachedFileUpload
      - Comment: The transcript text
      - Related contact: The original contact ID
    
    Note: Once the case is successfully created, downstream failures (linking contact,
    attaching file, adding comment) are logged but do not raise exceptions. This prevents
    duplicate case creation on SQS message retry.
    """
    logger.info(
        "Creating Connect Case",
        extra={
            "contactId": contact_id,
            "domainId": CASES_DOMAIN_ID,
            "templateId": case_template_id,
            "customerId": customer_id,
            "callerNumber": caller_number,
        },
    )

    case_id = None
    case_arn = None
    
    try:
        # Read envelope JSON to check for genaiSummary field
        case_summary = "Voicemail Summary: [Transcript available in comments]"
        try:
            envelope_obj = s3.get_object(Bucket=VMAIL_BUCKET, Key=json_key)
            envelope = json.loads(envelope_obj["Body"].read().decode("utf-8"))
            
            # When genaiSummary exists, add "Voicemail Summary: " prefix
            if "genaiSummary" in envelope:
                genai_summary = envelope["genaiSummary"]
                case_summary = f"Voicemail Summary: {genai_summary}"
                logger.info(
                    "Adding GenAI summary to case",
                    extra={"contactId": contact_id, "summaryLength": len(case_summary)},
                )
            else:
                logger.debug(
                    "No GenAI summary available, using fallback message",
                    extra={"contactId": contact_id},
                )
        except Exception as exc:
            logger.warning(
                "Failed to read envelope for GenAI summary – using fallback message",
                extra={"bucket": VMAIL_BUCKET, "key": json_key, "error": str(exc)},
            )
        
        # Truncate summary if it exceeds Cases API field length limit (3000 characters for summary field)
        MAX_SUMMARY_LENGTH = 3000
        if len(case_summary) > MAX_SUMMARY_LENGTH:
            case_summary = case_summary[:MAX_SUMMARY_LENGTH - 1] + "…"
            logger.info(
                "Summary truncated to fit Cases API limit",
                extra={"contactId": contact_id, "truncatedLength": len(case_summary)},
            )
        
        # Create the case with required fields (customer_id and title) and summary
        case_title = f"Voicemail from {caller_number} - Contact {contact_id}"
        
        create_case_params = {
            "domainId": CASES_DOMAIN_ID,
            "templateId": case_template_id,
            "fields": [
                {
                    "id": "customer_id",
                    "value": {"stringValue": customer_id}
                },
                {
                    "id": "title",
                    "value": {"stringValue": case_title}
                },
                {
                    "id": "summary",
                    "value": {"stringValue": case_summary}
                },
            ],
        }
        logger.info(
            "Calling connectcases.create_case",
            extra={"params": create_case_params, "contactId": contact_id},
        )
        case_response = connectcases.create_case(**create_case_params)
        
        case_id = case_response["caseId"]
        case_arn = case_response["caseArn"]
        
        logger.info(
            "Connect Case created successfully",
            extra={"caseId": case_id, "caseArn": case_arn, "contactId": contact_id},
        )
        metrics.add_metric(name="CaseCreated", unit=MetricUnit.Count, value=1)
        
    except Exception as exc:
        logger.error(
            "Failed to create Connect Case",
            extra={"contactId": contact_id, "error": str(exc)},
        )
        metrics.add_metric(name="CaseCreationFailed", unit=MetricUnit.Count, value=1)
        raise  # Re-raise to trigger SQS retry since case was not created
    
    # Case created successfully - downstream failures should not trigger retry
    # to prevent duplicate case creation
    
    # Link the original contact to the case
    try:
        contact_arn = f"arn:aws:connect:{region}:{account_id}:instance/{CONNECT_INSTANCE_ID}/contact/{contact_id}"
        connectcases.create_related_item(
            caseId=case_id,
            domainId=CASES_DOMAIN_ID,
            type="Contact",
            content={
                "contact": {
                    "contactArn": contact_arn
                }
            }
        )
        logger.info(
            "Original contact linked to case",
            extra={"caseId": case_id, "contactId": contact_id, "contactArn": contact_arn},
        )
        metrics.add_metric(name="CaseContactLinked", unit=MetricUnit.Count, value=1)
    except Exception as exc:
        logger.warning(
            "Failed to link contact to case (case already created)",
            extra={"caseId": case_id, "contactId": contact_id, "error": str(exc)},
        )
        metrics.add_metric(name="CaseContactLinkFailed", unit=MetricUnit.Count, value=1)
    
    # Attach the voicemail WAV file using Connect StartAttachedFileUpload
    try:
            file_name = wav_key.split("/")[-1]  # Extract filename from key
            file_size = _get_file_size(VMAIL_BUCKET, wav_key)
            
            # Step 1: Use Connect API to start attached file upload
            upload_response = connect.start_attached_file_upload(
                InstanceId=CONNECT_INSTANCE_ID,
                FileName=file_name,
                FileSizeInBytes=file_size,
                FileUseCaseType="ATTACHMENT",
                AssociatedResourceArn=case_arn,
                ClientToken=contact_id,  # Idempotency token
            )
            
            upload_url = upload_response["UploadUrlMetadata"]["Url"]
            headers_to_include = upload_response["UploadUrlMetadata"]["HeadersToInclude"]
            file_id = upload_response["FileId"]
            file_arn = upload_response["FileArn"]
            
            logger.info(
                "StartAttachedFileUpload response details",
                extra={
                    "fileId": file_id,
                    "fileArn": file_arn,
                    "headerCount": len(headers_to_include) if isinstance(headers_to_include, dict) else 0,
                    "headerKeys": list(headers_to_include.keys()) if isinstance(headers_to_include, dict) else [],
                    "contactId": contact_id
                },
            )
            
            # Download WAV from S3
            wav_obj = s3.get_object(Bucket=VMAIL_BUCKET, Key=wav_key)
            wav_data = wav_obj["Body"].read()
            
            # Step 2: Upload to the presigned S3 URL with the required headers from AWS
            # HeadersToInclude is a dict with all required headers
            import requests
            
            logger.info(
                "Uploading WAV to presigned URL",
                extra={"headerKeys": list(headers_to_include.keys()), "fileSize": file_size, "contactId": contact_id},
            )
            
            upload_result = requests.put(upload_url, data=wav_data, headers=headers_to_include)
            upload_result.raise_for_status()
            
            logger.info(
                "File uploaded to S3, completing attachment",
                extra={"fileId": file_id, "statusCode": upload_result.status_code, "contactId": contact_id},
            )
            
            # Step 3: Complete the attached file upload to finalize
            connect.complete_attached_file_upload(
                InstanceId=CONNECT_INSTANCE_ID,
                FileId=file_id,
                AssociatedResourceArn=case_arn,
            )
            
        logger.info(
            "Voicemail WAV attached to case",
            extra={"caseId": case_id, "fileName": file_name, "fileSize": file_size, "fileArn": file_arn},
        )
        metrics.add_metric(name="CaseFileAttached", unit=MetricUnit.Count, value=1)
    except Exception as exc:
        logger.warning(
            "Failed to attach WAV file to case (case already created)",
            extra={"caseId": case_id, "error": str(exc)},
        )
        metrics.add_metric(name="CaseFileAttachmentFailed", unit=MetricUnit.Count, value=1)
    
    # Add transcript as a comment (last so it appears at the bottom)
    if transcript:
        try:
            connectcases.create_related_item(
                caseId=case_id,
                domainId=CASES_DOMAIN_ID,
                type="Comment",
                content={
                    "comment": {
                        "body": f"Voicemail Transcript:\n\n{transcript}",
                        "contentType": "Text/Plain"
                    }
                }
            )
            logger.info(
                "Transcript added as comment to case",
                extra={"caseId": case_id, "contactId": contact_id},
            )
            metrics.add_metric(name="CaseCommentAdded", unit=MetricUnit.Count, value=1)
        except Exception as exc:
            logger.warning(
                "Failed to add transcript comment to case (case already created)",
                extra={"caseId": case_id, "error": str(exc)},
            )
            metrics.add_metric(name="CaseCommentAddFailed", unit=MetricUnit.Count, value=1)


def _get_file_size(bucket: str, key: str) -> int:
    """Get the size of an S3 object in bytes."""
    response = s3.head_object(Bucket=bucket, Key=key)
    return response["ContentLength"]
