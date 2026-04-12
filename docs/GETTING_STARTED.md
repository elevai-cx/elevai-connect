# Getting Started

**Duration:** 15-20 minutes
**Level:** Beginner

## What You'll Deploy

- Amazon Connect instance with full storage configuration
- S3 buckets with KMS encryption
- CloudWatch monitoring (70+ alarms)
- Lambda functions for custom integrations
- Business User Interface (data tables, workspaces, views)
- Voicemail with transcription
- Optional: Amazon Q in Connect (AI agent assistance)
- Optional: SAML authentication
- Optional: Customer Profiles
- Optional: Analytics Data Lake with Athena

## Prerequisites

- AWS CLI configured with credentials
- Python 3.13+ installed
- Pulumi CLI installed ([install guide](https://www.pulumi.com/docs/iac/download-install/))
- AWS permissions for Connect, S3, Lambda, IAM
- **For SAML**: SAML metadata XML file from your IdP

## Step 1: Clone and Setup Environment

```bash
git clone https://github.com/elevai-cx/elevai-connect.git
cd elevai-connect
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Step 2: Configure Pulumi

```bash
pulumi login --local  # Or use Pulumi Cloud / S3 backend
pulumi stack init dev
```

Copy the example config:

```bash
cp Pulumi.dev.yaml.example Pulumi.dev.yaml
```

## Step 3: Edit Configuration

Edit `Pulumi.dev.yaml` and update:

**Required:**

- `aws:region` - Your AWS region
- `alerting:error_email` - Email for critical alerts
- `billing:notificationEmail` - Email for budget alerts
- `connect:instanceAlias` - Globally unique, **cannot be changed after deployment**
- `connect:identityManagementType` - `SAML` or `CONNECT_MANAGED` (**cannot be changed after deployment**)

**Optional:**

- `connect:samlMetadataFile` - Path to SAML metadata (if using SAML)
- `billing:monthlyBudgetLimit` - Monthly budget in USD
- `qconnect:enabled` - Enable Amazon Q (`true`/`false`)
- `customer-profiles:enabled` - Enable Customer Profiles (`true`/`false`)

## Step 4: Preview Changes

```bash
pulumi preview --stack dev
```

Review the resources that will be created.

## Step 5: Deploy

```bash
pulumi up --stack dev
```

Wait for completion (~5-10 minutes). Review and approve the changes when prompted.

## Step 6: View Outputs

```bash
pulumi stack output
```

Save important outputs:

- Connect instance ID and ARN
- S3 bucket names
- Q Assistant ID (if enabled)
- SNS topic ARNs

## Step 7: Post-Deployment Steps

A few things need manual configuration in the AWS Console after deployment.

### Enable Contact Flow Features

Open AWS Console > Amazon Connect > Your Instance > Flows:

1. [Enable Automated Interaction Logs](https://docs.aws.amazon.com/connect/latest/adminguide/monitor-automated-interaction-logs.html)
2. [Enable Lex Bot Management](https://docs.aws.amazon.com/connect/latest/adminguide/enable-bot-building.html)

### Subscribe to SNS Alert Topics

Check your email for AWS SNS subscription confirmation messages and click the confirmation links. You should receive 2-3 emails depending on your configuration.

```bash
# Get your topic ARNs
pulumi stack output sns_info_warning_topic_arn
pulumi stack output sns_error_topic_arn
pulumi stack output sns_billing_topic_arn
```

### Customer Profiles Domain Association

**Only if you enabled Customer Profiles.**

```bash
# Check if needed
pulumi stack output customer_profiles_manual_setup_required
```

If the output is `true`:

1. Go to AWS Console > Amazon Connect > Your Instance
2. Navigate to **Data storage** > **Customer Profiles**
3. Click **Select domain** and choose `connect-profiles-domain`
4. Configure auto-association type (check `pulumi stack output customer_profiles_auto_association_type`)
5. If you enabled the error queue, paste the ARN from `pulumi stack output customer_profiles_error_queue_arn`
6. Click **Save**

## Step 8: Verify Deployment

- Log into your Amazon Connect instance
- Confirm SNS subscription emails are confirmed
- Check CloudWatch alarms are active in the AWS Console
- Test a basic inbound call

## Step 9: SAML Setup (if applicable)

If you chose SAML authentication, follow the [SAML Setup Guide](SAML_SETUP_GUIDE.md) for:

- Configuring your identity provider
- Assigning users
- Testing authentication

## Common Issues

| Issue | Solution |
|---|---|
| "Instance alias already exists" | Choose a different globally unique alias |
| Authentication errors | Run `aws sts get-caller-identity` to verify credentials |
| Region not supported | Check [Connect region availability](https://docs.aws.amazon.com/connect/latest/adminguide/regions.html) |
| Missing permissions | Review IAM permissions needed for Connect, S3, Lambda, IAM |

## Next Steps

- [Custom Extensions Guide](CUSTOM_EXTENSIONS_GUIDE.md) - Add your own AWS resources
- [Monitoring Guide](MONITORING_GUIDE.md) - Understand the 70+ CloudWatch alarms
- [Amazon Q Guide](AMAZON_Q_GUIDE.md) - Set up AI agent assistance
- [BUI Guide](BUI_GUIDE.md) - Configure the Business User Interface
- [Analytics Data Lake Guide](ANALYTICS_DATA_LAKE.md) - Query contact centre data with SQL
