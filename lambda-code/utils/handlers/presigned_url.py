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
Presigned URL Handler

Generates presigned S3 URLs for voicemail objects (WAV recordings and JSON
transcripts) stored in the vmail bucket. S3 URIs are passed in the form
s3://bucket-name/key/path and resolved to HTTPS presigned URLs.

Expected Parameters:
    s3Uri      - S3 URI to generate a presigned URL for (required)
                 e.g. s3://s3-vmail-27d105f/voicemails/2026/03/31/vmail-xxx.json
    expiry     - Optional override for URL expiry in seconds (default: 3600 / 60 mins)

Returns:
    {
        "statusCode": 200,
        "presignedUrl": "https://...",
        "bucket": "s3-vmail-27d105f",
        "key": "voicemails/2026/03/31/vmail-xxx.json",
        "expiry": "3600"
    }
"""

import os
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(child=True)
tracer = Tracer()

DEFAULT_EXPIRY_SECONDS = 3600  # 60 minutes


def _parse_s3_uri(s3_uri: str):
    """
    Parse an S3 URI into (bucket, key).

    Args:
        s3_uri: URI in the form s3://bucket-name/path/to/object

    Returns:
        (bucket, key) tuple

    Raises:
        ValueError: if the URI is not a valid s3:// URI
    """
    if not s3_uri.startswith("s3://"):
        raise ValueError(f"Invalid S3 URI (must start with s3://): {s3_uri!r}")

    without_scheme = s3_uri[5:]  # strip "s3://"
    slash_idx = without_scheme.find("/")

    if slash_idx == -1 or slash_idx == len(without_scheme) - 1:
        raise ValueError(f"Invalid S3 URI (missing key): {s3_uri!r}")

    bucket = without_scheme[:slash_idx]
    key = without_scheme[slash_idx + 1:]

    if not bucket:
        raise ValueError(f"Invalid S3 URI (empty bucket): {s3_uri!r}")

    return bucket, key


@tracer.capture_method
def handle(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Generate a presigned S3 URL for a vmail object.

    Args:
        event: Amazon Connect event
        context: Lambda context

    Returns:
        Response dict containing the presigned URL and metadata
    """
    parameters = event.get("Details", {}).get("Parameters", {})

    s3_uri = parameters.get("s3Uri", "").strip()
    if not s3_uri:
        logger.warning("Missing required parameter: s3Uri")
        return {
            "statusCode": 400,
            "body": "Missing required parameter: s3Uri",
            "error": True,
        }

    # Optional expiry override
    expiry_seconds = DEFAULT_EXPIRY_SECONDS
    if "expiry" in parameters:
        try:
            expiry_seconds = int(parameters["expiry"])
            if expiry_seconds <= 0:
                raise ValueError("expiry must be a positive integer")
        except (ValueError, TypeError) as exc:
            logger.warning(f"Invalid expiry parameter: {parameters['expiry']!r} — {exc}")
            return {
                "statusCode": 400,
                "body": f"Invalid expiry parameter: {parameters['expiry']!r}",
                "error": True,
            }

    # Parse the S3 URI
    try:
        bucket, key = _parse_s3_uri(s3_uri)
    except ValueError as exc:
        logger.warning(str(exc))
        return {
            "statusCode": 400,
            "body": str(exc),
            "error": True,
        }

    logger.info("Generating presigned URL", extra={
        "bucket": bucket,
        "key": key,
        "expiry_seconds": expiry_seconds,
    })

    # Generate the presigned URL
    try:
        s3_client = boto3.client("s3")
        presigned_url = s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expiry_seconds,
        )
    except ClientError as exc:
        error_code = exc.response["Error"]["Code"]
        logger.exception("Failed to generate presigned URL", extra={
            "error_code": error_code,
            "bucket": bucket,
            "key": key,
        })
        return {
            "statusCode": 500,
            "body": f"Failed to generate presigned URL: {error_code}",
            "error": True,
        }

    logger.info("Presigned URL generated successfully", extra={
        "bucket": bucket,
        "key": key,
        "expiry_seconds": expiry_seconds,
    })

    return {
        "statusCode": 200,
        "presignedUrl": presigned_url,
        "bucket": bucket,
        "key": key,
        "expiry": str(expiry_seconds),
    }
