# Getting Started

**Duration:** 15-20 minutes  
**Level:** Beginner

## What You'll Deploy

- Amazon Connect instance
- S3 buckets with encryption
- CloudWatch monitoring (70+ alarms)
- Lambda functions
- Optional: Amazon Q in Connect
- Optional: SAML authentication

## Prerequisites

- AWS CLI configured with credentials
- Python 3.13+ installed
- Pulumi CLI installed
- AWS permissions for Connect, S3, Lambda, IAM
- **For SAML**: SAML metadata XML file from your IdP

## Step 1: Clone and Setup Environment

```bash
git clone https://github.com/bloy.me.uk/elevai-connect.git
cd elevai-connect
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Step 2: Configure Pulumi

```bash
pulumi login --local # Use Pulumi Cloud or local backend. S3 can be used: https://www.pulumi.com/docs/iac/concepts/state-and-backends/#using-a-diy-backend
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
- `alerting:error_email` - Your email for critical alerts
- `billing:notificationEmail` - Your email for budget alerts
- `connect:instanceAlias` - **Globally unique, PERMANENT**
- `connect:identityManagementType` - `SAML` or `CONNECT_MANAGED` (**PERMANENT**)

**Optional:**
- `connect:samlMetadataFile` - Path to SAML metadata (if using SAML)
- `billing:monthlyBudgetLimit` - Monthly budget in USD
- `qconnect:enabled` - Enable Amazon Q (true/false)

> **Warning:** `instanceAlias` and `identityManagementType` cannot be changed after deployment!

## Step 4: Preview Changes

```bash
pulumi preview --stack dev
```

Review the resources to be created.

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
- Connect instance ID
- Connect instance ARN
- S3 bucket names
- Q Assistant ID (if enabled)

## Step 7: Post-Deployment Manual Steps

Complete these in AWS Console (API limitations):

Open up AWS Console > Amazon Connect > Your instance > Flows

1. **[Enable Automated Interaction Logs](https://docs.aws.amazon.com/connect/latest/adminguide/monitor-automated-interaction-logs.html)**
2. **[Enable Lex Bot Management](https://docs.aws.amazon.com/connect/latest/adminguide/enable-bot-building.html)**
3. Verify **Next Generation Amazon Connect** is enabled

For the full post-deployment checklist see [POST_DEPLOYMENT_STEPS.md](POST_DEPLOYMENT_STEPS.md).

## Step 8: Verify Deployment

- Log into Amazon Connect instance
- Check email for SNS subscription confirmations
- Verify CloudWatch alarms in AWS Console
- Test basic functionality

## Step 9: SAML Setup (if applicable)

Follow the [SAML Configuration Guide](SAML_SETUP_GUIDE.md) for:
- Finalizing IdP configuration
- User assignment
- Testing authentication

## Common Issues

| Issue                           | Solution                                  |
| ------------------------------- | ----------------------------------------- |
| "Instance alias already exists" | Choose a different globally unique alias  |
| Authentication errors           | Verify: `aws sts get-caller-identity`     |
| Region not supported            | Check Connect availability in your region |
| Missing permissions             | Review IAM permissions in README.md       |

## Next Steps

- **Customize:** Add resources in `custom/` directory - see [Custom Extensions Guide](CUSTOM_EXTENSIONS_GUIDE.md)
- **Monitor:** Review CloudWatch alarms - see [Monitoring Guide](MONITORING_GUIDE.md)
- **AI:** Set up Amazon Q knowledge base - see [Amazon Q Guide](AMAZON_Q_GUIDE.md)
- **Scale:** Review service quotas for production
