# Parameter Store Guide

This guide explains how to extend elevai-connect by using the exposed data within Parameter store

---

## 🎯 Overview

Part of the deployment of elevai-connect, is a set of Parameter Store items that expose key information that you then use within your own IaC.

All parameters use the prefix `/elevai/` for easy identification and organization.

---

## 📦 Available Parameters

### Amazon Connect Instance

- `/elevai/connect/instance/alias` - Instance alias
- `/elevai/connect/instance/arn` - Instance ARN

### S3 Buckets

Each bucket has both name and ARN parameters:

- `/elevai/s3/contact-records/name` and `/arn` - Contact trace records from Firehose
- `/elevai/s3/call-recordings/name` and `/arn`
- `/elevai/s3/chat-transcripts/name` and `/arn`
- `/elevai/s3/exported-reports/name` and `/arn`
- `/elevai/s3/attachments/name` and `/arn`
- `/elevai/s3/screen-recordings/name` and `/arn`
- `/elevai/s3/contact-evaluations/name` and `/arn`
- `/elevai/s3/email-messages/name` and `/arn`
- `/elevai/s3/qconnect-knowledge-base/name` and `/arn` (if QConnect enabled)

### Kinesis Firehose

- `/elevai/kinesis/firehose/contact-records/arn` - Firehose stream for contact trace records

### KMS Encryption

- `/elevai/kms/data-encryption-key/id` - KMS key ID
- `/elevai/kms/data-encryption-key/arn` - KMS key ARN

### IAM SAML (only with SAML authentication)

- `/elevai/iam/saml-provider/name` - SAML provider name
- `/elevai/iam/saml-provider/arn` - SAML provider ARN
- `/elevai/iam/saml-role/name` - SAML role name
- `/elevai/iam/saml-role/arn` - SAML role ARN

### SNS Topics

- `/elevai/sns/alerts/info-warning/arn` - Info and warning alerts topic
- `/elevai/sns/alerts/error/arn` - Error alerts topic
- `/elevai/sns/alerts/billing/arn` - Billing and budget alerts topic (if billing alarms enabled)

---

## 💡 Usage Examples

### AWS CLI

```bash
# Get the Connect instance ARN
aws ssm get-parameter --name "/elevai/connect/instance/arn" --query "Parameter.Value" --output text

# Get the recordings bucket name
aws ssm get-parameter --name "/elevai/s3/call-recordings/name" --query "Parameter.Value" --output text
```

### Terraform

```hcl
data "aws_ssm_parameter" "connect_instance_arn" {
  name = "/elevai/connect/instance/arn"
}

resource "aws_lambda_function" "example" {
  environment {
    variables = {
      CONNECT_INSTANCE_ARN = data.aws_ssm_parameter.connect_instance_arn.value
    }
  }
}
```

### CloudFormation

```yaml
Parameters:
  ConnectInstanceArn:
    Type: AWS::SSM::Parameter::Value<String>
    Default: /elevai/connect/instance/arn

Resources:
  MyLambdaFunction:
    Type: AWS::Lambda::Function
    Properties:
      Environment:
        Variables:
          CONNECT_INSTANCE_ARN: !Ref ConnectInstanceArn
```

### Python (boto3)

```python
import boto3

ssm = boto3.client('ssm')

# Get single parameter
response = ssm.get_parameter(Name='/elevai/connect/instance/arn')
instance_arn = response['Parameter']['Value']

# Get multiple parameters
response = ssm.get_parameters_by_path(
    Path='/elevai/',
    Recursive=True
)

for param in response['Parameters']:
    print(f"{param['Name']}: {param['Value']}")
```

---

## 🔍 Discovering Parameters

List all elevai parameters:

```bash
aws ssm get-parameters-by-path \
  --path "/elevai/" \
  --recursive \
  --query "Parameters[*].[Name,Description]" \
  --output table
```

---

## 📝 Notes

- All parameters are of type `String`
- Parameters are created with the `ParameterStore: true` tag for easy filtering
- Parameters are only created for resources that are actually deployed
- SAML parameters only exist when using SAML authentication
- QConnect bucket parameters only exist when QConnect is enabled
