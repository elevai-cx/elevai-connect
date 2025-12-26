# Deploy elevai-connect Workshop

**Duration:** 15-20 minutes  
**Level:** Beginner  
**Mode:** Interactive with Claude Code

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

## Workshop Steps

### Step 1: Clone and Setup Environment

```bash
git clone https://github.com/bloy.me.uk/elevai-connect.git
cd elevai-connect
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Configure Pulumi

```bash
pulumi login --local # Use Pulumi Cloud or local backend. S3 can be used: https://www.pulumi.com/docs/iac/concepts/state-and-backends/#using-a-diy-backend
pulumi stack init dev
```

Copy the example config:
```bash
cp Pulumi.dev.yaml.example Pulumi.dev.yaml
```

### Step 3: Edit Configuration

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

⚠️ **Warning:** `instanceAlias` and `identityManagementType` cannot be changed after deployment!

### Step 4: Preview Changes

Ask Claude Code to run:
```
pulumi preview --stack dev
```

Review the resources to be created. Ask questions about anything unclear.

### Step 5: Deploy

Ask Claude Code to deploy using the MCP tool (never use bash `pulumi up`):
```
Use the pulumi_up MCP tool to deploy with stack=dev
```

Wait for completion (~5-10 minutes).

### Step 6: View Outputs

```bash
pulumi stack output
```

Save important outputs:
- Connect instance ID
- Connect instance ARN
- S3 bucket names
- Q Assistant ID (if enabled)

### Step 7: Post-Deployment Manual Steps

Complete these in AWS Console (API limitations):

Open up AWS Console > Amazon Connect > Your instance > Flows

1. **[Enable Automated Interaction Logs](https://docs.aws.amazon.com/connect/latest/adminguide/monitor-automated-interaction-logs.html)**
2. **[Enable Lex Bot Management](https://docs.aws.amazon.com/connect/latest/adminguide/enable-bot-building.html)**
3. Verify **Next Generation Amazon Connect** is enabled

### Step 8: Verify Deployment

- Log into Amazon Connect instance
- Check email for SNS subscription confirmations
- Verify CloudWatch alarms in AWS Console
- Test basic functionality

### Step 9: SAML Setup (if applicable)

Follow the [SAML Configuration Guide](../../docs/SAML_SETUP_GUIDE.md) for:
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

- **Customize:** Add resources in `custom/` directory
- **Monitor:** Review CloudWatch alarms and dashboards
- **Learn:** Try the Amazon Q Knowledge Base workshop
- **Scale:** Review service quotas for production

## Using Claude Code

Throughout this workshop, you can ask Claude Code:
- "What's the current status?"
- "Explain this config option"
- "Preview my changes"
- "Deploy the stack"
- "What resources were created?"
- "Help me troubleshoot [issue]"

Claude Code can read your config, run Pulumi commands, and guide you through each step interactively.

## Resources

- [Project README](../../README.md) - Complete documentation
- [SAML Setup Guide](../../docs/SAML_SETUP_GUIDE.md)
- [Monitoring Guide](../../docs/MONITORING_GUIDE.md)
- [Amazon Q Guide](../../docs/AMAZON_Q_GUIDE.md)

---

**Need help?** Ask Claude Code any questions during the workshop!
