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
Kinesis Stream Alarms

Defines CloudWatch alarms for both Kinesis Data Streams and Kinesis Video Streams.
"""

from typing import Dict, Optional, List
import pulumi
import pulumi_aws as aws

from .alerting import AlarmConfig, AlertingInfrastructure
from .config_helpers import (
    get_alarm_threshold,
    get_alarm_period,
    get_alarm_evaluation_periods
)


def create_kinesis_data_stream_alarms(
    streams: Dict[str, Optional[aws.kinesis.Stream]],
    alerting: AlertingInfrastructure
) -> None:
    """
    Create CloudWatch alarms for Kinesis Data Streams.
    
    Monitors the recommended metrics from AWS best practices:
    - GetRecords.IteratorAgeMilliseconds: Read position lag (data loss risk)
    - ReadProvisionedThroughputExceeded: Read throttling
    - WriteProvisionedThroughputExceeded: Write throttling
    - PutRecords.Success: Write success rate
    - GetRecords.Success: Read success rate
    
    Args:
        streams: Dictionary of stream names to Kinesis Stream resources
        alerting: Alerting infrastructure instance
    """
    
    for stream_name, stream in streams.items():
        if stream is None:
            continue
        
        stream_display_name = stream_name.replace("_", "-")
        
        # Get the stream name for dimensions
        stream_resource_name = stream.name
        
        # 1. Iterator Age (CRITICAL - Data Loss Risk)
        # Alert when read position is behind 50% of retention period
        iterator_age_threshold = get_alarm_threshold(
            "kinesisDataStreams", 
            "iteratorAgeMilliseconds", 
            43200000  # 12 hours (50% of 24hr default)
        )
        
        alerting.create_alarm(AlarmConfig(
            name=f"kinesis-data-{stream_display_name}-iterator-age",
            description=(
                f"Kinesis Data Stream {stream_display_name} read position is behind. "
                f"Risk of data loss if iterator age exceeds retention period."
            ),
            metric_name="GetRecords.IteratorAgeMilliseconds",
            namespace="AWS/Kinesis",
            statistic="Maximum",
            period=get_alarm_period("kinesisDataStreams", "iteratorAgeMilliseconds", 300),
            evaluation_periods=get_alarm_evaluation_periods(
                "kinesisDataStreams", "iteratorAgeMilliseconds", 2
            ),
            threshold=iterator_age_threshold,
            comparison_operator="GreaterThanThreshold",
            severity="ERROR",
            dimensions={"StreamName": stream_resource_name},
            treat_missing_data="notBreaching"
        ))
        
        # 2. Read Throughput Exceeded (WARNING - Throttling)
        alerting.create_alarm(AlarmConfig(
            name=f"kinesis-data-{stream_display_name}-read-throttled",
            description=(
                f"Kinesis Data Stream {stream_display_name} is experiencing read throttling. "
                f"Consumer reads are being rate limited."
            ),
            metric_name="ReadProvisionedThroughputExceeded",
            namespace="AWS/Kinesis",
            statistic="Average",
            period=get_alarm_period("kinesisDataStreams", "readThroughputExceeded", 300),
            evaluation_periods=get_alarm_evaluation_periods(
                "kinesisDataStreams", "readThroughputExceeded", 2
            ),
            threshold=get_alarm_threshold("kinesisDataStreams", "readThroughputExceeded", 0.01),
            comparison_operator="GreaterThanThreshold",
            severity="WARNING",
            dimensions={"StreamName": stream_resource_name},
            treat_missing_data="notBreaching"
        ))
        
        # 3. Write Throughput Exceeded (WARNING - Throttling)
        alerting.create_alarm(AlarmConfig(
            name=f"kinesis-data-{stream_display_name}-write-throttled",
            description=(
                f"Kinesis Data Stream {stream_display_name} is experiencing write throttling. "
                f"Producer writes are being rate limited."
            ),
            metric_name="WriteProvisionedThroughputExceeded",
            namespace="AWS/Kinesis",
            statistic="Average",
            period=get_alarm_period("kinesisDataStreams", "writeThroughputExceeded", 300),
            evaluation_periods=get_alarm_evaluation_periods(
                "kinesisDataStreams", "writeThroughputExceeded", 2
            ),
            threshold=get_alarm_threshold("kinesisDataStreams", "writeThroughputExceeded", 0.01),
            comparison_operator="GreaterThanThreshold",
            severity="WARNING",
            dimensions={"StreamName": stream_resource_name},
            treat_missing_data="notBreaching"
        ))
        
        # 4. PutRecords Success Rate (ERROR - Write Failures)
        alerting.create_alarm(AlarmConfig(
            name=f"kinesis-data-{stream_display_name}-put-records-failures",
            description=(
                f"Kinesis Data Stream {stream_display_name} PutRecords success rate is below threshold. "
                f"Records are failing to write to the stream."
            ),
            metric_name="PutRecords.Success",
            namespace="AWS/Kinesis",
            statistic="Average",
            period=get_alarm_period("kinesisDataStreams", "putRecordsSuccess", 300),
            evaluation_periods=get_alarm_evaluation_periods(
                "kinesisDataStreams", "putRecordsSuccess", 2
            ),
            threshold=get_alarm_threshold("kinesisDataStreams", "putRecordsSuccess", 0.95),
            comparison_operator="LessThanThreshold",
            severity="ERROR",
            dimensions={"StreamName": stream_resource_name},
            treat_missing_data="notBreaching"
        ))
        
        # 5. GetRecords Success Rate (ERROR - Read Failures)
        alerting.create_alarm(AlarmConfig(
            name=f"kinesis-data-{stream_display_name}-get-records-failures",
            description=(
                f"Kinesis Data Stream {stream_display_name} GetRecords success rate is below threshold. "
                f"Consumers are failing to read from the stream."
            ),
            metric_name="GetRecords.Success",
            namespace="AWS/Kinesis",
            statistic="Average",
            period=get_alarm_period("kinesisDataStreams", "getRecordsSuccess", 300),
            evaluation_periods=get_alarm_evaluation_periods(
                "kinesisDataStreams", "getRecordsSuccess", 2
            ),
            threshold=get_alarm_threshold("kinesisDataStreams", "getRecordsSuccess", 0.95),
            comparison_operator="LessThanThreshold",
            severity="ERROR",
            dimensions={"StreamName": stream_resource_name},
            treat_missing_data="notBreaching"
        ))


def create_kinesis_video_stream_alarms(
    kvs_config: Optional[aws.connect.InstanceStorageConfig],
    alerting: AlertingInfrastructure
) -> None:
    """
    Create CloudWatch alarms for Kinesis Video Streams.
    
    Monitors connection and error metrics for KVS streaming:
    - GetMedia.ConnectionErrors: Connection errors when consumers retrieve streams
    - PutMedia.ConnectionErrors: Connection errors when streaming to KVS (from Connect)
    - PutMedia.ErrorAckCount: Fragment acknowledgment errors from KVS backend
    
    Important: KVS metrics are aggregated across all streams with a given prefix,
    not per individual stream. Amazon Connect creates individual KVS streams
    per call/interaction.
    
    Args:
        kvs_config: Kinesis Video Streams configuration (or None if disabled)
        alerting: Alerting infrastructure instance
    """
    
    if kvs_config is None:
        pulumi.log.info("Kinesis Video Streams not enabled, skipping alarms")
        return
    
    # Get the KVS prefix from config
    config = pulumi.Config("kinesisVideoStream")
    prefix = config.get("prefix") or "elevai"
    
    # KVS metrics are at the account level, not per-stream
    # We monitor connection health and error indicators
    
    # 1. GetMedia Connection Errors (WARNING - Consumer Connection Issues)
    alerting.create_alarm(AlarmConfig(
        name="kinesis-video-get-media-connection-errors",
        description=(
            f"Kinesis Video Streams (prefix: {prefix}) experiencing GetMedia connection errors. "
            f"Consumers are having trouble connecting to retrieve video streams."
        ),
        metric_name="GetMedia.ConnectionErrors",
        namespace="AWS/KinesisVideo",
        statistic="Sum",
        period=get_alarm_period("kinesisVideoStreams", "getMediaConnectionErrors", 300),
        evaluation_periods=get_alarm_evaluation_periods(
            "kinesisVideoStreams", "getMediaConnectionErrors", 2
        ),
        threshold=get_alarm_threshold("kinesisVideoStreams", "getMediaConnectionErrors", 5),
        comparison_operator="GreaterThanThreshold",
        severity="WARNING",
        treat_missing_data="notBreaching"
    ))
    
    # 2. PutMedia Connection Errors (ERROR - Stream Ingestion Issues)
    alerting.create_alarm(AlarmConfig(
        name="kinesis-video-put-media-connection-errors",
        description=(
            f"Kinesis Video Streams (prefix: {prefix}) experiencing PutMedia connection errors. "
            f"Amazon Connect is having trouble streaming media to KVS."
        ),
        metric_name="PutMedia.ConnectionErrors",
        namespace="AWS/KinesisVideo",
        statistic="Sum",
        period=get_alarm_period("kinesisVideoStreams", "putMediaConnectionErrors", 300),
        evaluation_periods=get_alarm_evaluation_periods(
            "kinesisVideoStreams", "putMediaConnectionErrors", 2
        ),
        threshold=get_alarm_threshold("kinesisVideoStreams", "putMediaConnectionErrors", 5),
        comparison_operator="GreaterThanThreshold",
        severity="ERROR",
        treat_missing_data="notBreaching"
    ))
    
    # 3. PutMedia Error Acknowledgment Count (ERROR - Fragment Processing Errors)
    alerting.create_alarm(AlarmConfig(
        name="kinesis-video-put-media-error-ack",
        description=(
            f"Kinesis Video Streams (prefix: {prefix}) experiencing fragment acknowledgment errors. "
            f"KVS backend is rejecting or failing to process fragments from Amazon Connect."
        ),
        metric_name="PutMedia.ErrorAckCount",
        namespace="AWS/KinesisVideo",
        statistic="Sum",
        period=get_alarm_period("kinesisVideoStreams", "putMediaErrorAckCount", 300),
        evaluation_periods=get_alarm_evaluation_periods(
            "kinesisVideoStreams", "putMediaErrorAckCount", 2
        ),
        threshold=get_alarm_threshold("kinesisVideoStreams", "putMediaErrorAckCount", 10),
        comparison_operator="GreaterThanThreshold",
        severity="ERROR",
        treat_missing_data="notBreaching"
    ))


def get_kinesis_alarm_configs() -> Dict[str, List[dict]]:
    """
    Get documentation for Kinesis alarms.
    
    Returns alarm configurations for documentation purposes, split by stream type.
    
    Returns:
        Dictionary with 'data_streams' and 'video_streams' keys containing
        lists of alarm configuration dictionaries
    """
    return {
        "data_streams": [
            {
                "name": "Iterator Age",
                "severity": "ERROR",
                "description": "Read position lag - risk of data loss if iterator age exceeds retention",
                "config_key": "alarms:kinesisDataStreams:iteratorAgeMilliseconds",
                "default_threshold": "43200000 ms (12 hours)",
                "default_period": "300 seconds (5 minutes)",
                "default_evaluation_periods": 2,
                "action": "Investigate consumer lag. Scale consumers or increase processing capacity."
            },
            {
                "name": "Read Throughput Exceeded",
                "severity": "WARNING",
                "description": "Consumers are being throttled due to read limits",
                "config_key": "alarms:kinesisDataStreams:readThroughputExceeded",
                "default_threshold": "0.01 (1% throttled)",
                "default_period": "300 seconds (5 minutes)",
                "default_evaluation_periods": 2,
                "action": "Consider using enhanced fan-out or increasing shard count."
            },
            {
                "name": "Write Throughput Exceeded",
                "severity": "WARNING",
                "description": "Producers are being throttled due to write limits",
                "config_key": "alarms:kinesisDataStreams:writeThroughputExceeded",
                "default_threshold": "0.01 (1% throttled)",
                "default_period": "300 seconds (5 minutes)",
                "default_evaluation_periods": 2,
                "action": "Increase shard count or implement producer backoff/retry logic."
            },
            {
                "name": "PutRecords Success",
                "severity": "ERROR",
                "description": "Records failing to write to stream",
                "config_key": "alarms:kinesisDataStreams:putRecordsSuccess",
                "default_threshold": "0.95 (95% success)",
                "default_period": "300 seconds (5 minutes)",
                "default_evaluation_periods": 2,
                "action": "Check producer logs for errors. Verify IAM permissions and network connectivity."
            },
            {
                "name": "GetRecords Success",
                "severity": "ERROR",
                "description": "Consumers failing to read from stream",
                "config_key": "alarms:kinesisDataStreams:getRecordsSuccess",
                "default_threshold": "0.95 (95% success)",
                "default_period": "300 seconds (5 minutes)",
                "default_evaluation_periods": 2,
                "action": "Check consumer logs. Verify shard iterator validity and consumer configuration."
            }
        ],
        "video_streams": [
            {
                "name": "GetMedia Connection Errors",
                "severity": "WARNING",
                "description": "Connection errors when consumers retrieve video streams",
                "config_key": "alarms:kinesisVideoStreams:getMediaConnectionErrors",
                "default_threshold": "5 errors",
                "default_period": "300 seconds (5 minutes)",
                "default_evaluation_periods": 2,
                "action": "Check consumer network connectivity and KVS endpoint accessibility."
            },
            {
                "name": "PutMedia Connection Errors",
                "severity": "ERROR",
                "description": "Connection errors when Amazon Connect streams to KVS",
                "config_key": "alarms:kinesisVideoStreams:putMediaConnectionErrors",
                "default_threshold": "5 errors",
                "default_period": "300 seconds (5 minutes)",
                "default_evaluation_periods": 2,
                "action": "Check Amazon Connect instance network and KVS service health."
            },
            {
                "name": "PutMedia Error Acknowledgment",
                "severity": "ERROR",
                "description": "Fragment acknowledgment errors from KVS backend",
                "config_key": "alarms:kinesisVideoStreams:putMediaErrorAckCount",
                "default_threshold": "10 errors",
                "default_period": "300 seconds (5 minutes)",
                "default_evaluation_periods": 2,
                "action": "Check KVS backend health and fragment format/size. May indicate service degradation."
            }
        ]
    }
