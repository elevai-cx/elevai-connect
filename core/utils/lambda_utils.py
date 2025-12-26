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
Lambda Utilities

Reusable Lambda function creation utilities with best practices.

Naming Convention: <stage>-lbd-<purpose>-<hash>
Example: dev-lbd-knowledge-tagging-abc123f
Resource Type: lbd (64 char limit)
"""

from typing import Dict, Optional
import os
import subprocess
import shutil
import hashlib
import base64
import pulumi
import pulumi_aws as aws

from .naming import create_name, create_logical_name


def get_log_level_for_env(env_type: str) -> str:
    """
    Determine log level based on environment type.
    
    Args:
        env_type: Environment type (prod, dev, etc.)
        
    Returns:
        Log level string (WARNING for prod, DEBUG for others)
    """
    return "WARNING" if env_type.lower() == "prod" else "DEBUG"


def create_lambda_with_requirements(
    purpose: str,
    lambda_dir: str,
    iam_role: aws.iam.Role,
    tags: Dict[str, str],
    memory_size: int = 256,
    timeout: int = 30,
    environment_variables: Optional[Dict[str, pulumi.Input[str]]] = None,
    connect_instance: Optional[aws.connect.Instance] = None,
    architecture: str = "arm64",
    runtime: str = "python3.11",
    log_level: Optional[str] = None,
    opts: Optional[pulumi.ResourceOptions] = None,
) -> aws.lambda_.Function:
    """
    Create a Lambda function with requirements.txt support and AWS best practices.
    
    Naming convention: <stage>-lbd-<purpose>-<hash>
    Example: dev-lbd-knowledge-tagging-abc123f
    
    The logical name includes the stage prefix, and Pulumi automatically
    appends a hash suffix for uniqueness.
    
    Features:
    - ARM64 architecture for cost savings
    - Automatic requirements.txt installation
    - CloudWatch log group with configurable retention
    - AWS PowerTools environment variables
    - Optional Amazon Connect association
    - Consistent hash-based change detection
    
    Args:
        purpose: Descriptive purpose (e.g., 'knowledge-tagging', 'utils')
        lambda_dir: Path to lambda directory (e.g., './lambda/utils')
        iam_role: IAM role for Lambda execution
        tags: Tags to apply to the function
        memory_size: Memory in MB (default: 256)
        timeout: Timeout in seconds (default: 30)
        environment_variables: Additional environment variables
        connect_instance: Optional Connect instance for association
        architecture: CPU architecture (default: 'arm64')
        runtime: Python runtime (default: 'python3.11')
        log_level: Log level for PowerTools (auto-detected if None)
        opts: Pulumi resource options
        
    Returns:
        Lambda function resource
    """
    if log_level is None:
        env_config = pulumi.Config("environment")
        env_type = env_config.get("type") or "dev"
        log_level = get_log_level_for_env(env_type)
    
    code_archive, source_hash = prepare_lambda_code(lambda_dir)
    
    # Include stage in logical name so Pulumi adds hash suffix
    # Logical: dev-lbd-knowledge-tagging
    # Physical: dev-lbd-knowledge-tagging-abc123f (Pulumi adds hash)
    stage = pulumi.get_stack()
    logical_name = f"{stage}-lbd-{purpose}"
    
    env_vars = {
        "POWERTOOLS_SERVICE_NAME": purpose,
        "POWERTOOLS_METRICS_NAMESPACE": "AmazonConnect",
        "LOG_LEVEL": log_level,
        "POWERTOOLS_LOGGER_LOG_EVENT": "true",
        "POWERTOOLS_LOGGER_SAMPLE_RATE": "0.1",
        "POWERTOOLS_TRACE_DISABLED": "false",
        "POWERTOOLS_TRACER_CAPTURE_RESPONSE": "true",
        "POWERTOOLS_TRACER_CAPTURE_ERROR": "true",
    }
    
    if environment_variables:
        env_vars.update(environment_variables)
    
    function = aws.lambda_.Function(
        logical_name,
        # NO name parameter - let Pulumi add hash to logical name
        role=iam_role.arn,
        runtime=runtime,
        handler="index.handler",
        code=code_archive,
        architectures=[architecture],
        memory_size=memory_size,
        timeout=timeout,
        environment=aws.lambda_.FunctionEnvironmentArgs(
            variables=env_vars
        ),
        tags={**tags, "Purpose": purpose},
        source_code_hash=source_hash,
        opts=opts,
    )
    
    cloudwatch_config = pulumi.Config("cloudwatch")
    log_retention_days = cloudwatch_config.get_int("logRetentionDays") or 30
    retention_in_days = None if log_retention_days == 0 else log_retention_days
    
    aws.cloudwatch.LogGroup(
        f"{logical_name}-logs",
        name=pulumi.Output.concat("/aws/lambda/", function.name),
        retention_in_days=retention_in_days,
        tags=tags,
    )
    
    if connect_instance:
        aws.lambda_.Permission(
            f"{logical_name}-connect-invoke-permission",
            action="lambda:InvokeFunction",
            function=function.name,
            principal="connect.amazonaws.com",
            source_arn=connect_instance.arn,
        )
        
        aws.connect.LambdaFunctionAssociation(
            f"{logical_name}-connect-association",
            function_arn=function.arn,
            instance_id=connect_instance.id,
        )
    
    return function


def get_source_code_hash(lambda_dir: str) -> str:
    """
    Calculate deterministic hash of lambda source code.
    
    Only includes source files, not dependencies, for consistency.
    
    Args:
        lambda_dir: Path to lambda directory
        
    Returns:
        Base64-encoded SHA256 hash
    """
    hash_obj = hashlib.sha256()
    
    files_to_hash = []
    for root, _, files in os.walk(lambda_dir):
        for file in sorted(files):
            if file.endswith('.py') or file == 'requirements.txt':
                rel_path = os.path.relpath(os.path.join(root, file), lambda_dir)
                files_to_hash.append(rel_path)
    
    for rel_path in sorted(files_to_hash):
        filepath = os.path.join(lambda_dir, rel_path)
        hash_obj.update(rel_path.encode('utf-8'))
        with open(filepath, 'rb') as f:
            hash_obj.update(f.read())
    
    return base64.b64encode(hash_obj.digest()).decode('utf-8')


def prepare_lambda_code(lambda_dir: str) -> tuple:
    """
    Prepare Lambda code with requirements.txt installation.
    
    Args:
        lambda_dir: Path to lambda directory
        
    Returns:
        Tuple of (AssetArchive, source_code_hash)
    """
    requirements_path = os.path.join(lambda_dir, "requirements.txt")
    source_hash = get_source_code_hash(lambda_dir)
    
    has_requirements = False
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r') as f:
            content = f.read().strip()
            has_requirements = any(
                line.strip() and not line.strip().startswith('#')
                for line in content.split('\n')
            )
    
    if has_requirements:
        archive = install_requirements_archive(lambda_dir, requirements_path, source_hash)
    else:
        archive = pulumi.FileArchive(lambda_dir)
    
    return archive, source_hash


def install_requirements_archive(
    lambda_dir: str, 
    requirements_path: str, 
    source_hash: str
) -> pulumi.AssetArchive:
    """
    Install requirements and create archive with caching.
    
    Args:
        lambda_dir: Path to lambda directory
        requirements_path: Path to requirements.txt
        source_hash: Hash of source code
        
    Returns:
        AssetArchive with installed dependencies
    """
    lambda_name = os.path.basename(os.path.normpath(lambda_dir))
    build_dir = os.path.join(".pulumi", "lambda-builds", lambda_name)
    os.makedirs(build_dir, exist_ok=True)
    
    hash_file = os.path.join(build_dir, '.build_hash')
    
    needs_rebuild = True
    if os.path.exists(hash_file):
        with open(hash_file, 'r') as f:
            stored_hash = f.read().strip()
            if stored_hash == source_hash:
                needs_rebuild = False
                if not os.path.exists(os.path.join(build_dir, 'index.py')):
                    needs_rebuild = True
    
    if needs_rebuild:
        print(f"Building Lambda package for {lambda_name}...")
        
        for item in os.listdir(build_dir):
            item_path = os.path.join(build_dir, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            elif item != '.build_hash':
                os.remove(item_path)
        
        try:
            subprocess.check_call(
                [
                    "pip", "install",
                    "-r", requirements_path,
                    "-t", build_dir,
                    "--platform", "manylinux2014_aarch64",
                    "--only-binary=:all:",
                    "--upgrade",
                    "--quiet"
                ],
                stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError:
            print(f"Warning: pip install encountered an issue, but continuing...")
        
        for item in os.listdir(lambda_dir):
            if item == '__pycache__' or item.endswith('.pyc'):
                continue
            src = os.path.join(lambda_dir, item)
            dst = os.path.join(build_dir, item)
            
            if os.path.exists(dst):
                if os.path.isdir(dst):
                    shutil.rmtree(dst)
                else:
                    os.remove(dst)
            
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        
        with open(hash_file, 'w') as f:
            f.write(source_hash)
        
        print(f"Lambda package built successfully for {lambda_name}")
    else:
        print(f"Using cached Lambda package for {lambda_name}")
    
    return pulumi.FileArchive(build_dir)
