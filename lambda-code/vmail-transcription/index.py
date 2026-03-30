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
Voicemail Processor Lambda (elevai-connect-vmail)

Triggered by SQS messages sourced from EventBridge Amazon Connect
DISCONNECTED contact events that carry the tag elevai-connect-vmail=true.

Processing steps:
1. Parse the contact event from the SQS body.
2. Derive the S3 key for the IVR recording from the initiationTimestamp and contactId.
3. Download the WAV file from the call-recordings bucket.
4. Trim the audio to [start_time, end_time] using the contact tags:
     - elevai-connect-vmail-start-time  (required)
     - elevai-connect-vmail-end-time    (optional; falls back to disconnectTimestamp)
5. Upload the trimmed voicemail WAV to the vmail bucket under:
     voicemails/<YYYY>/<MM>/<DD>/<contactId>.wav
6. Start an async Amazon Transcribe batch job and exit immediately.
   The transcription result is handled by the vmail-transcription Lambda.
"""

import io
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import wave

import boto3
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit

# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

logger = Logger(service=os.getenv("POWERTOOLS_SERVICE_NAME", "vmail-processor"))
tracer = Tracer(service=os.getenv("POWERTOOLS_SERVICE_NAME", "vmail-processor"))
metrics = Metrics(
    namespace=os.getenv("POWERTOOLS_METRICS_NAMESPACE", "AmazonConnect"),
    service=os.getenv("POWERTOOLS_SERVICE_NAME", "vmail-processor"),
)

RECORDINGS_BUCKET = os.environ["RECORDINGS_BUCKET"]
VMAIL_BUCKET = os.environ["VMAIL_BUCKET"]
RECORDINGS_PREFIX = os.getenv("RECORDINGS_PREFIX", "call-recordings/ivr")
TRANSCRIBE_LANGUAGE = os.getenv("TRANSCRIBE_LANGUAGE_CODE", "en-GB")
TRANSCRIBE_AUTO_DETECT = os.getenv("TRANSCRIBE_AUTO_DETECT_LANGUAGE", "false").lower() == "true"
# Comma-separated list of candidate languages for auto-detection (improves accuracy)
TRANSCRIBE_LANGUAGE_OPTIONS = [
    l.strip() for l in os.getenv("TRANSCRIBE_LANGUAGE_OPTIONS", "").split(",") if l.strip()
]

s3 = boto3.client("s3")
transcribe = boto3.client("transcribe")


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

@tracer.capture_lambda_handler
@logger.inject_lambda_context
@metrics.log_metrics
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """SQS batch handler with partial failure support."""
    records: List[Dict] = event.get("Records", [])
    metrics.add_metric(name="VmailInvocation", unit=MetricUnit.Count, value=1)
    metrics.add_metric(name="SQSRecordsReceived", unit=MetricUnit.Count, value=len(records))

    batch_item_failures: List[Dict] = []

    for record in records:
        message_id = record.get("messageId")
        try:
            _process_record(record)
        except Exception as exc:
            logger.error("Failed to process record", extra={"message_id": message_id, "error": str(exc)})
            metrics.add_metric(name="RecordFailed", unit=MetricUnit.Count, value=1)
            batch_item_failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": batch_item_failures}


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

@tracer.capture_method
def _process_record(record: Dict[str, Any]) -> None:
    contact_event = json.loads(record.get("body", "{}"))
    detail = contact_event.get("detail", {})
    contact_id: str = detail.get("contactId", "")
    # instanceId is not in the event detail, we need to get it from the instanceArn
    instance_arn: str = detail.get("instanceArn", "")
    # Extract instance ID from ARN: arn:aws:connect:region:account:instance/instance-id
    instance_id = instance_arn.split("/")[-1] if instance_arn else ""
    
    # Extract account ID and region from the top-level event
    account_id = contact_event.get("account", "")
    region = contact_event.get("region", "")

    logger.info("Processing voicemail contact", extra={
        "contactId": contact_id, 
        "instanceId": instance_id,
        "accountId": account_id,
        "region": region
    })

    # ------------------------------------------------------------------
    # Get contact attributes using Connect API
    # ------------------------------------------------------------------
    if not instance_id:
        logger.error("Missing instanceId - cannot retrieve contact attributes", extra={"contactId": contact_id})
        raise ValueError(f"Missing instanceId for contact {contact_id}")
    
    connect_client = boto3.client("connect")
    try:
        attrs_response = connect_client.get_contact_attributes(
            InstanceId=instance_id,
            InitialContactId=contact_id,
        )
        contact_attributes = attrs_response.get("Attributes", {})
        logger.info("Retrieved contact attributes", extra={"contactId": contact_id, "attributeCount": len(contact_attributes)})
    except Exception as exc:
        logger.error("Failed to get contact attributes", extra={"contactId": contact_id, "error": str(exc)})
        raise

    # ------------------------------------------------------------------
    # Resolve timing
    # ------------------------------------------------------------------
    start_time = _parse_iso(contact_attributes.get("elevai-connect-vmail-start-time"))
    end_time = _parse_iso(
        contact_attributes.get("elevai-connect-vmail-end-time") or detail.get("disconnectTimestamp")
    )

    if start_time is None:
        raise ValueError(f"Missing elevai-connect-vmail-start-time attribute on contact {contact_id}")
    if end_time is None:
        raise ValueError(f"Cannot determine end time for contact {contact_id}")

    duration_ms = int((end_time - start_time).total_seconds() * 1000)
    if duration_ms <= 0:
        logger.warning("Voicemail window is zero or negative – skipping", extra={"contactId": contact_id})
        metrics.add_metric(name="VmailSkippedZeroDuration", unit=MetricUnit.Count, value=1)
        return

    # ------------------------------------------------------------------
    # Locate, download and trim the recording
    # ------------------------------------------------------------------
    initiation_ts = _parse_iso(detail.get("initiationTimestamp"))
    recording_key = _resolve_recording_key(contact_id, initiation_ts)

    logger.info("Downloading recording", extra={"bucket": RECORDINGS_BUCKET, "key": recording_key})
    wav_bytes = _download_wav_bytes(RECORDINGS_BUCKET, recording_key)

    if initiation_ts is not None:
        offset_ms = max(0, int((start_time - initiation_ts).total_seconds() * 1000))
    else:
        offset_ms = 0

    trimmed = _trim_wav(wav_bytes, offset_ms, duration_ms)

    # ------------------------------------------------------------------
    # Upload trimmed voicemail WAV
    # ------------------------------------------------------------------
    dest_key = _build_dest_key(contact_id, start_time)
    _upload_wav(trimmed, VMAIL_BUCKET, dest_key)

    logger.info(
        "Voicemail WAV stored",
        extra={
            "contactId": contact_id,
            "destBucket": VMAIL_BUCKET,
            "destKey": dest_key,
            "durationMs": duration_ms,
        },
    )
    metrics.add_metric(name="VmailStored", unit=MetricUnit.Count, value=1)
    metrics.add_metric(name="VmailDurationMs", unit=MetricUnit.Milliseconds, value=duration_ms)

    # ------------------------------------------------------------------
    # Write .metadata sidecar so downstream Lambdas have queue ARN etc.
    # ------------------------------------------------------------------
    _write_metadata(contact_id, dest_key, start_time, contact_attributes, detail, account_id, region)

    # ------------------------------------------------------------------
    # Start async Transcribe job and exit — result handled by
    # the vmail-transcription Lambda via EventBridge job state change.
    # Job name encodes contactId and dest_key so the transcription
    # Lambda can write the JSON to the correct location without needing
    # any additional state store.
    # ------------------------------------------------------------------
    _start_transcribe_job(contact_id, dest_key)


# ---------------------------------------------------------------------------
# Metadata sidecar
# ---------------------------------------------------------------------------

@tracer.capture_method
def _write_metadata(
    contact_id: str,
    wav_key: str,
    start_time: datetime,
    contact_attributes: Dict[str, str],
    detail: Dict[str, Any],
    account_id: str,
    region: str,
) -> None:
    """
    Write a JSON sidecar (<contactId>.metadata) alongside the WAV file.

    Captured fields:
      - contactId
      - accountId (from event)
      - region (from event)
      - All elevai-connect-vmail-* attributes from contact attributes
      - startTime / disconnectTimestamp
    """
    queue_arn = contact_attributes.get("elevai-connect-vmail-queue-arn", "")
    if not queue_arn:
        logger.warning(
            "elevai-connect-vmail-queue-arn attribute not present – task routing will be unavailable",
            extra={"contactId": contact_id},
        )

    destination_channel = contact_attributes.get("elevai-connect-vmail-destination-channel", "task")
    case_template_id = contact_attributes.get("elevai-connect-vmail-destination-case-template-id", "")
    customer_id = contact_attributes.get("elevai-connect-vmail-customer-id", "")

    metadata = {
        "contactId": contact_id,
        "accountId": account_id,
        "region": region,
        "elevai-connect-vmail-queue-arn": queue_arn,
        "elevai-connect-vmail-destination-channel": destination_channel,
        "elevai-connect-vmail-destination-case-template-id": case_template_id,
        "elevai-connect-vmail-customer-id": customer_id,
        "elevai-connect-vmail-caller-number": contact_attributes.get("elevai-connect-vmail-caller-number", ""),
        "elevai-connect-vmail-genai-summary": contact_attributes.get("elevai-connect-vmail-genai-summary", "false"),
        "elevai-connect-vmail-genai-prompt": contact_attributes.get("elevai-connect-vmail-genai-prompt", ""),
        "elevai-connect-vmail-start-time": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "disconnectTimestamp": detail.get("disconnectTimestamp", ""),
        "initiationTimestamp": detail.get("initiationTimestamp", ""),
        "attributes": contact_attributes,
    }

    metadata_key = wav_key.replace(".wav", ".metadata")
    s3.put_object(
        Bucket=VMAIL_BUCKET,
        Key=metadata_key,
        Body=json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    logger.info(
        "Metadata sidecar written",
        extra={"bucket": VMAIL_BUCKET, "key": metadata_key, "queueArn": queue_arn},
    )


# ---------------------------------------------------------------------------
# Transcribe
# ---------------------------------------------------------------------------

@tracer.capture_method
def _start_transcribe_job(contact_id: str, wav_key: str) -> None:
    """
    Submit an async Transcribe batch job for the uploaded voicemail WAV.

    Job name format: vmail-<contactId>-<epoch>
    The output is directed to the same vmail bucket so Transcribe writes
    its raw result there; the transcription Lambda then enriches and
    normalises it into the final JSON envelope.

    The wav_key is embedded in the job name after base64-safe encoding
    so the transcription Lambda can reconstruct the target path without
    a database lookup.
    """
    import base64
    encoded_key = base64.urlsafe_b64encode(wav_key.encode()).decode().rstrip("=")
    # Keep job name within the 200-char Transcribe limit
    job_name = f"vmail-{contact_id}-{int(time.time())}"

    media_uri = f"s3://{VMAIL_BUCKET}/{wav_key}"

    # Derive the output key (alongside the WAV, same prefix, .json extension)
    output_key = wav_key.replace(".wav", ".json")
    output_key_prefix = output_key.rsplit("/", 1)[0] + "/"

    logger.info(
        "Starting Transcribe job",
        extra={
            "jobName": job_name,
            "mediaUri": media_uri,
            "outputBucket": VMAIL_BUCKET,
            "outputKeyPrefix": output_key_prefix,
            "languageCode": TRANSCRIBE_LANGUAGE,
        },
    )

    # Verify the WAV object actually exists before handing off to Transcribe
    try:
        head = s3.head_object(Bucket=VMAIL_BUCKET, Key=wav_key)
        logger.info(
            "WAV object confirmed in S3",
            extra={
                "bucket": VMAIL_BUCKET,
                "key": wav_key,
                "contentLength": head.get("ContentLength"),
                "contentType": head.get("ContentType"),
                "serverSideEncryption": head.get("ServerSideEncryption"),
            },
        )
    except Exception as head_err:
        logger.error(
            "WAV object not found in S3 before calling Transcribe",
            extra={"bucket": VMAIL_BUCKET, "key": wav_key, "error": str(head_err)},
        )
        raise

    job_params = {
        "TranscriptionJobName": job_name,
        "Media": {"MediaFileUri": media_uri},
        "MediaFormat": "wav",
        "OutputBucketName": VMAIL_BUCKET,
        "OutputKey": output_key_prefix,
        "Settings": {
            "ShowSpeakerLabels": False,
            "ChannelIdentification": False,
        },
        "Tags": [
            {"Key": "elevai-contact-id", "Value": contact_id},
            {"Key": "elevai-wav-key", "Value": wav_key},
        ],
    }

    if TRANSCRIBE_AUTO_DETECT:
        job_params["IdentifyLanguage"] = True
        if TRANSCRIBE_LANGUAGE_OPTIONS:
            job_params["LanguageOptions"] = TRANSCRIBE_LANGUAGE_OPTIONS
        logger.info(
            "Using auto language detection",
            extra={"languageOptions": TRANSCRIBE_LANGUAGE_OPTIONS or "all"},
        )
    else:
        job_params["LanguageCode"] = TRANSCRIBE_LANGUAGE
        logger.info("Using fixed language code", extra={"languageCode": TRANSCRIBE_LANGUAGE})

    transcribe.start_transcription_job(**job_params)

    logger.info(
        "Transcribe job started",
        extra={"jobName": job_name, "mediaUri": media_uri, "outputPrefix": output_key_prefix},
    )
    metrics.add_metric(name="TranscribeJobStarted", unit=MetricUnit.Count, value=1)


# ---------------------------------------------------------------------------
# Audio helpers (pure-Python WAV trimming — no ffmpeg dependency)
# ---------------------------------------------------------------------------

def _download_wav_bytes(bucket: str, key: str) -> bytes:
    response = s3.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()


def _trim_wav(wav_bytes: bytes, offset_ms: int, duration_ms: int) -> bytes:
    """
    Trim a WAV file to [offset_ms, offset_ms + duration_ms] using the
    stdlib wave module. Works on standard PCM WAV files (which Amazon
    Connect IVR recordings always are) with no native dependencies.
    """
    with wave.open(io.BytesIO(wav_bytes), "rb") as src:
        frame_rate = src.getframerate()
        n_channels = src.getnchannels()
        sample_width = src.getsampwidth()
        total_frames = src.getnframes()

        frames_per_ms = frame_rate / 1000.0
        start_frame = int(offset_ms * frames_per_ms)
        end_frame = min(int((offset_ms + duration_ms) * frames_per_ms), total_frames)
        n_frames = max(0, end_frame - start_frame)

        src.setpos(start_frame)
        raw_frames = src.readframes(n_frames)

    out = io.BytesIO()
    with wave.open(out, "wb") as dst:
        dst.setnchannels(n_channels)
        dst.setsampwidth(sample_width)
        dst.setframerate(frame_rate)
        dst.writeframes(raw_frames)

    return out.getvalue()


def _upload_wav(wav_bytes: bytes, bucket: str, key: str) -> None:
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=wav_bytes,
        ContentType="audio/wav",
    )


# ---------------------------------------------------------------------------
# S3 key resolution
# ---------------------------------------------------------------------------

def _resolve_recording_key(contact_id: str, initiation_ts: Optional[datetime]) -> str:
    """
    Build the expected S3 key for an IVR recording.

    Convention observed in the bucket:
      call-recordings/ivr/<YYYY>/<MM>/<DD>/<contactId>_<YYYYMMDD>T<HH:MM>_UTC.wav

    Falls back to a prefix scan if the exact key is not found.
    """
    if initiation_ts:
        y = initiation_ts.strftime("%Y")
        m = initiation_ts.strftime("%m")
        d = initiation_ts.strftime("%d")
        hhmm = initiation_ts.strftime("%H:%M")
        date_compact = initiation_ts.strftime("%Y%m%d")
        candidate = f"{RECORDINGS_PREFIX}/{y}/{m}/{d}/{contact_id}_{date_compact}T{hhmm}_UTC.wav"

        try:
            s3.head_object(Bucket=RECORDINGS_BUCKET, Key=candidate)
            return candidate
        except s3.exceptions.ClientError:
            logger.warning(
                "Candidate recording key not found, falling back to prefix scan",
                extra={"candidate": candidate},
            )

    prefix = RECORDINGS_PREFIX
    if initiation_ts:
        prefix = f"{RECORDINGS_PREFIX}/{initiation_ts.strftime('%Y/%m/%d')}/{contact_id}"

    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=RECORDINGS_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            key: str = obj["Key"]
            if contact_id in key and key.endswith(".wav"):
                return key

    raise FileNotFoundError(
        f"Recording not found for contact {contact_id} under s3://{RECORDINGS_BUCKET}/{prefix}"
    )


def _build_dest_key(contact_id: str, start_time: datetime) -> str:
    return f"voicemails/{start_time.strftime('%Y/%m/%d')}/{contact_id}.wav"


# ---------------------------------------------------------------------------
# Timestamp parsing
# ---------------------------------------------------------------------------

def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    value = value.rstrip("Z").replace("Z", "")
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        value = value[:26]
        dt = datetime.fromisoformat(value)
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
