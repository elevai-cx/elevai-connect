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
Timestamp Handler

Returns the current UTC (Zulu) time as an ISO 8601 string.
Intended for use in Amazon Connect contact flows where a start time
tag is needed — e.g. to later trim a WAV recording to exact timestamps.
"""

from datetime import datetime, timezone
from typing import Dict, Any
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(child=True)
tracer = Tracer()


@tracer.capture_method
def handle(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Return the current UTC timestamp in ISO 8601 / Zulu format.

    The contact flow should call this at the point you want to mark
    (e.g. immediately after the greeting prompt) and store the result
    as a contact attribute / tag via a Set contact attributes block.

    Returns:
        {
            "statusCode": 200,
            "timestamp": "2026-03-28T19:42:02.368Z",   # Zulu / UTC
            "timestamp-epoch": "1743191322368"           # milliseconds since epoch
        }
    """
    now = datetime.now(timezone.utc)

    zulu = now.strftime('%Y-%m-%dT%H:%M:%S.') + f"{now.microsecond // 1000:03d}Z"
    epoch_ms = str(int(now.timestamp() * 1000))

    logger.info("Generated timestamp", extra={
        "timestamp": zulu,
        "epoch_ms": epoch_ms
    })

    return {
        "statusCode": 200,
        "timestamp": zulu,
        "timestamp-epoch": epoch_ms
    }
