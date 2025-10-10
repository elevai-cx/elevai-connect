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
Lambda Functions

Creates Lambda functions for Amazon Connect integrations and event handlers.
"""

from typing import Dict, Optional
import os
import subprocess
import tempfile
import shutil
import hashlib
import pulumi
import pulumi_aws as aws


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
    name: str,
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
    Create a Lambda function with support for requirements.txt.
    
    This helper handles all common Lambda configuration including:
    - ARM64 architecture
    - Memory and timeout settings
    - Requirements.txt installation
    - CloudWatch log group creation (retention configurable via cloudwatch:logRetentionDays)
    - AWS PowerTools environment variables
    - Optional Amazon Connect association
    
    Args:
        name: Name for the Lambda function resource
        lambda_dir: Path to the lambda function directory (e.g., './lambda/utils')
        iam_role: IAM role for Lambda execution
        tags: Tags to apply to the function
        memory_size: Memory allocation in MB (default: 256)
        timeout: Timeout in seconds (default: 30)
        environment_variables: Optional additional environment variables
        connect_instance: Optional Connect instance for association
        architecture: CPU architecture (default: 'arm64')
        runtime: Python runtime version (default: 'python3.11')
        log_level: Log level for PowerTools (default: auto-detected from env)
        opts: Optional Pulumi resource options (e.g., for depends_on)
        
    Returns:
        Lambda function resource
    """
    
    # Auto-detect log level from environment if not specified
    if log_level is None:
        env_config = pulumi.Config("environment")
        env_type = env_config.get("type") or "dev"
        log_level = get_log_level_for_env(env_type)
    
    # Prepare the code archive with consistent hashing
    code_archive, source_hash = prepare_lambda_code(lambda_dir)
    
    # Build environment variables with PowerTools defaults
    env_vars = {
        # AWS PowerTools configuration
        "POWERTOOLS_SERVICE_NAME": name,
        "POWERTOOLS_METRICS_NAMESPACE": "AmazonConnect",
        "LOG_LEVEL": log_level,
        "POWERTOOLS_LOGGER_LOG_EVENT": "true",
        "POWERTOOLS_LOGGER_SAMPLE_RATE": "0.1",
        "POWERTOOLS_TRACE_DISABLED": "false",
        "POWERTOOLS_TRACER_CAPTURE_RESPONSE": "true",
        "POWERTOOLS_TRACER_CAPTURE_ERROR": "true",
        "POWERTOOLS_METRICS_NAMESPACE": "AmazonConnect",
    }
    
    # Merge with any additional environment variables provided
    if environment_variables:
        env_vars.update(environment_variables)
    
    # Create the Lambda function
    function = aws.lambda_.Function(
        name,
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
        tags={**tags, "Name": name},
        # Use source code hash for consistent change detection across machines
        source_code_hash=source_hash,
        opts=opts,
    )
    
    # Create CloudWatch log group with retention
    cloudwatch_config = pulumi.Config("cloudwatch")
    log_retention_days = cloudwatch_config.get_int("logRetentionDays")
    
    # Default to 30 days if not specified
    if log_retention_days is None:
        log_retention_days = 30
    
    # If retention is 0, set to None (never expire)
    retention_in_days = None if log_retention_days == 0 else log_retention_days
    
    aws.cloudwatch.LogGroup(
        f"{name}-logs",
        name=pulumi.Output.concat("/aws/lambda/", function.name),
        retention_in_days=retention_in_days,
        tags=tags,
    )
    
    # Associate with Amazon Connect if instance provided
    if connect_instance:
        # Grant Connect permission to invoke Lambda
        aws.lambda_.Permission(
            f"{name}-connect-invoke-permission",
            action="lambda:InvokeFunction",
            function=function.name,
            principal="connect.amazonaws.com",
            source_arn=connect_instance.arn,
        )
        
        # Associate the Lambda function with Connect instance
        aws.connect.LambdaFunctionAssociation(
            f"{name}-connect-association",
            function_arn=function.arn,
            instance_id=connect_instance.id,
        )
    
    return function


def get_source_code_hash(lambda_dir: str) -> str:
    """
    Calculate a deterministic hash of the lambda source code.
    
    This hash only includes source files, not installed dependencies,
    making it consistent across machines and CI/CD runs.
    
    Args:
        lambda_dir: Path to the lambda function directory
        
    Returns:
        Base64-encoded SHA256 hash of the source code
    """
    import base64
    
    hash_obj = hashlib.sha256()
    
    # Hash all Python files and requirements.txt in sorted order
    files_to_hash = []
    for root, _, files in os.walk(lambda_dir):
        for file in sorted(files):
            if file.endswith('.py') or file == 'requirements.txt':
                rel_path = os.path.relpath(os.path.join(root, file), lambda_dir)
                files_to_hash.append(rel_path)
    
    # Sort to ensure consistent ordering
    for rel_path in sorted(files_to_hash):
        filepath = os.path.join(lambda_dir, rel_path)
        # Hash the relative path first for uniqueness
        hash_obj.update(rel_path.encode('utf-8'))
        # Then hash the file contents
        with open(filepath, 'rb') as f:
            hash_obj.update(f.read())
    
    # Return base64-encoded hash (AWS Lambda format)
    return base64.b64encode(hash_obj.digest()).decode('utf-8')


def prepare_lambda_code(lambda_dir: str) -> tuple:
    """
    Prepare Lambda code including requirements.txt installation.
    
    Args:
        lambda_dir: Path to the lambda function directory
        
    Returns:
        Tuple of (AssetArchive, source_code_hash)
    """
    requirements_path = os.path.join(lambda_dir, "requirements.txt")
    
    # Calculate source code hash (excludes dependencies)
    source_hash = get_source_code_hash(lambda_dir)
    
    # Check if requirements.txt exists and has content
    has_requirements = False
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r') as f:
            content = f.read().strip()
            # Check if file has actual package requirements (not just comments)
            has_requirements = any(
                line.strip() and not line.strip().startswith('#')
                for line in content.split('\n')
            )
    
    if has_requirements:
        # Install requirements into a stable build directory
        archive = install_requirements_archive(lambda_dir, requirements_path, source_hash)
    else:
        # No requirements, just package the directory
        archive = pulumi.FileArchive(lambda_dir)
    
    return archive, source_hash


def install_requirements_archive(lambda_dir: str, requirements_path: str, source_hash: str) -> pulumi.AssetArchive:
    """
    Install requirements and create an archive.
    
    Uses a stable build directory with hash-based caching to avoid unnecessary rebuilds.
    
    Args:
        lambda_dir: Path to the lambda function directory
        requirements_path: Path to requirements.txt
        source_hash: Hash of the source code
        
    Returns:
        AssetArchive with installed dependencies
    """
    # Create a stable build directory based on the lambda directory name
    lambda_name = os.path.basename(os.path.normpath(lambda_dir))
    build_dir = os.path.join(".pulumi", "lambda-builds", lambda_name)
    
    # Create build directory if it doesn't exist
    os.makedirs(build_dir, exist_ok=True)
    
    # Store hash in build directory
    hash_file = os.path.join(build_dir, '.build_hash')
    
    # Check if we need to rebuild
    needs_rebuild = True
    if os.path.exists(hash_file):
        with open(hash_file, 'r') as f:
            stored_hash = f.read().strip()
            if stored_hash == source_hash:
                needs_rebuild = False
                # Verify build directory is valid
                if not os.path.exists(os.path.join(build_dir, 'index.py')):
                    needs_rebuild = True
    
    if needs_rebuild:
        print(f"Building Lambda package for {lambda_name}...")
        
        # Clean the build directory
        for item in os.listdir(build_dir):
            item_path = os.path.join(build_dir, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            elif item != '.build_hash':
                os.remove(item_path)
        
        # Install requirements to build directory
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
        except subprocess.CalledProcessError as e:
            print(f"Warning: pip install encountered an issue, but continuing...")
        
        # Copy lambda function files to build directory
        for item in os.listdir(lambda_dir):
            if item == '__pycache__' or item.endswith('.pyc'):
                continue
            src = os.path.join(lambda_dir, item)
            dst = os.path.join(build_dir, item)
            
            # Remove existing destination if it exists
            if os.path.exists(dst):
                if os.path.isdir(dst):
                    shutil.rmtree(dst)
                else:
                    os.remove(dst)
            
            # Copy the item
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        
        # Store the hash
        with open(hash_file, 'w') as f:
            f.write(source_hash)
        
        print(f"Lambda package built successfully for {lambda_name}")
    else:
        print(f"Using cached Lambda package for {lambda_name}")
    
    # Create archive from build directory
    return pulumi.FileArchive(build_dir)


def create_lambda_functions(
    connect_instance: aws.connect.Instance,
    iam_role: aws.iam.Role,
    tags: Dict[str, str]
) -> Dict[str, aws.lambda_.Function]:
    """
    Create Lambda functions for Amazon Connect.
    
    Args:
        connect_instance: Amazon Connect instance
        iam_role: IAM role for Lambda execution
        tags: Tags to apply to all functions
        
    Returns:
        Dictionary of function names to Lambda function resources
    """
    functions = {}
    
    # Utils function - common utilities for contact flows
    # Log level is auto-detected: DEBUG for dev, WARNING for prod
    utils_function = create_lambda_with_requirements(
        name="utils",
        lambda_dir="./lambda-code/utils",
        iam_role=iam_role,
        tags=tags,
        memory_size=512,
        timeout=7,
        connect_instance=connect_instance,
    )
    functions["utils"] = utils_function
    
    return functions
