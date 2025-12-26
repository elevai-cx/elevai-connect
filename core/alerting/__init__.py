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
Alerting Module

Provides CloudWatch alarms and SNS topic infrastructure for monitoring.
"""

from .alerting import create_alerting_infrastructure, AlertingInfrastructure
from .lambda_alarms import create_lambda_alarms
from .connect_alarms import create_connect_alarms
from .sqs_alarms import create_sqs_alarms
from .billing_alarms import create_billing_alarms
from .kinesis_alarms import (
    create_kinesis_data_stream_alarms,
    create_kinesis_video_stream_alarms
)

__all__ = [
    "create_alerting_infrastructure",
    "AlertingInfrastructure",
    "create_lambda_alarms",
    "create_connect_alarms",
    "create_sqs_alarms",
    "create_billing_alarms",
    "create_kinesis_data_stream_alarms",
    "create_kinesis_video_stream_alarms",
]
