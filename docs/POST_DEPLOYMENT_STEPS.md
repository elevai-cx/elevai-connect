# Post-Deployment Manual Steps

This document provides a consolidated checklist of all manual configuration steps required after deploying your Amazon Connect infrastructure with Pulumi.

> 💡 **Tip:** Copy this checklist to your project documentation and check off items as you complete them.

## Quick Status Check

Run these commands to see which features you've enabled:

```bash
# Check your configuration
pulumi config

# View all outputs (shows what was created)
pulumi stack output

# Check if Customer Profiles is enabled
pulumi stack output customer_profiles_manual_setup_required

# Check identity management type
pulumi config get connect:identityManagementType
```

---

## ✅ Required Steps (All Deployments)

These steps must be completed for all Amazon Connect deployments.

### 1. Enable Contact Flow Features

**📍 Location:** AWS Console → Amazon Connect → Your Instance → Flows

**Why:** These features require manual enablement due to AWS Console-only configuration.

- [ ] **Enable Automated Interaction Logs**
  - [Documentation](https://docs.aws.amazon.com/connect/latest/adminguide/monitor-automated-interaction-logs.html)
  - Enables detailed logging of contact flow execution
  - Essential for debugging contact flows

- [ ] **Enable Lex Bot Management & Analytics**
  - [Documentation](https://docs.aws.amazon.com/connect/latest/adminguide/enable-bot-building.html)
  - Required for Amazon Lex chatbot integration
  - Enables bot analytics and reporting

- [ ] **Verify Next Generation Amazon Connect is Enabled**
  - Should be enabled by default for new instances
  - Provides enhanced features and performance
  - If not enabled, contact AWS Support

**Verification:**
```bash
# These features don't have CLI verification
# Check in AWS Console under Flows settings
```

---

## 🔐 Conditional Steps (Based on Configuration)

These steps are only required if you've enabled specific features.

### 2. SAML Authentication Setup

**📋 Required if:** `connect:identityManagementType: SAML`

**Check if needed:**
```bash
pulumi config get connect:identityManagementType
# If output is "SAML", complete these steps

# Check if placeholder metadata was used
pulumi logs | grep "Using SAML placeholder"
# If this returns results, you MUST update the SAML metadata
```

**Steps:**

- [ ] **Configure Identity Provider (IdP)**
  - Set up SAML application in your IdP (Okta, Azure AD, Google Workspace, etc.)
  - Download SAML metadata XML from your IdP
  - Configure user attributes and mappings

- [ ] **Update SAML Metadata in AWS (if using placeholder)**
  - If you deployed without providing `connect:samlMetadataFile`, a placeholder was used
  - You must update this with your actual IdP metadata
  - **Option 1: Via AWS Console**
    - Go to: AWS Console → IAM → Identity Providers
    - Select `ConnectSAMLProvider`
    - Click **Edit**
    - Upload your IdP's SAML metadata XML
    - Click **Update provider**
  - **Option 2: Via AWS CLI**
    ```bash
    aws iam update-saml-provider \
      --saml-provider-arn $(pulumi stack output saml_provider_arn) \
      --saml-metadata-document file://path/to/your-idp-metadata.xml
    ```
  - **Option 3: Update Pulumi Config and Redeploy**
    ```bash
    # Add to Pulumi.<stack>.yaml
    connect:samlMetadataFile: "./path/to/your-idp-metadata.xml"
    
    # Redeploy
    pulumi up
    ```

- [ ] **Assign Users in IdP**
  - Add users to the SAML application
  - Configure security profile mappings
  - Set up user attributes (email, name, etc.)

- [ ] **Test User Login**
  - Have a test user attempt SAML login
  - Verify they can access Connect
  - Check their permissions match expected security profile

**📚 Complete Guide:** See [docs/SAML_SETUP_GUIDE.md](SAML_SETUP_GUIDE.md) for detailed instructions.

**Verification:**
```bash
# Test SAML login with a user account
# URL format: https://<instance-alias>.my.connect.aws/
```

---

### 3. Customer Profiles Domain Association

**📋 Required if:** `customer-profiles:enabled: true`

**Check if needed:**
```bash
pulumi stack output customer_profiles_manual_setup_required
# If output is "true", complete these steps
```

**Configuration Values You'll Need:**
```bash
# Get these values before starting
pulumi stack output customer_profiles_domain_name
pulumi stack output customer_profiles_auto_association_type
pulumi stack output customer_profiles_error_queue_arn  # If error queue enabled
```

**Steps:**

- [ ] **1. Navigate to Amazon Connect Console**
  - Go to: AWS Console → Amazon Connect → Your Instance

- [ ] **2. Access Customer Profiles Settings**
  - Left navigation → **Data storage** → **Customer Profiles**
  - Click **Select domain**

- [ ] **3. Associate the Domain**
  - Select domain: `connect-profiles-domain`
  - Click **Associate domain**

- [ ] **4. Configure Auto-Association**
  - Choose the auto-association type from your Pulumi output
  - Options:
    - `CREATE_LIMITED_PROFILES_AND_AUTO_ASSOCIATE` (Default)
    - `AUTO_ASSOCIATE_PROFILES_ONLY`
    - `CREATE_INFERRED_PROFILES_ONLY`

- [ ] **5. Configure Error Queue (if enabled)**
  - If you enabled `customer-profiles:error-queue: true`
  - Expand **Error handling** section
  - Paste the Error Queue ARN from Pulumi output

- [ ] **6. Save Configuration**
  - Click **Save** to complete the association

**📚 Complete Guide:** See [docs/CUSTOMER_PROFILES.md](CUSTOMER_PROFILES.md) for detailed documentation.

**Verification:**
```bash
# Make a test call through your Connect instance
# Wait 5-10 minutes for profile processing
# Then search for the profile:

aws customer-profiles search-profiles \
  --domain-name connect-profiles-domain \
  --key-name _phone \
  --values "+1234567890"  # Use your test number
```

---

### 4. Amazon Q Knowledge Base Content

**📋 Required if:** `qconnect:enabled: true`

**Check if needed:**
```bash
pulumi config get qconnect:enabled
# If output is "true", complete these steps
```

**Steps:**

- [ ] **1. Upload Knowledge Base Content**
  - Upload documents to the S3 bucket created by Pulumi
  - Get bucket name: `pulumi stack output qconnect_kb_bucket_name`
  - Organize content in folders matching your `qconnect:contentTagging` configuration

- [ ] **2. Verify Content Tagging**
  - Check that folder structure matches your configuration
  - Verify tags are applied correctly
  - Test content searchability

- [ ] **3. Enable Amazon Q in Connect**
  - Verify the assistant is active
  - Test agent suggestions

**📚 Complete Guide:** See [docs/AMAZON_Q_SETUP.md](AMAZON_Q_SETUP.md) for detailed instructions.

**Verification:**
```bash
# List content in knowledge base bucket
aws s3 ls s3://$(pulumi stack output qconnect_kb_bucket_name)/ --recursive

# Check Q Assistant status
aws qconnect get-assistant \
  --assistant-id $(pulumi stack output qconnect_assistant_id)
```

---

## 📋 Optional Enhancements

These steps are recommended for production deployments.

### 5. Subscribe to SNS Alert Topics

**Purpose:** Receive email notifications for alarms and monitoring alerts.

**Steps:**

- [ ] **Confirm SNS Subscriptions**
  - Check your email for AWS SNS subscription confirmation messages
  - Click the confirmation links
  - You should receive 2-3 confirmation emails depending on configuration

**Get Topic ARNs:**
```bash
pulumi stack output sns_info_warning_topic_arn
pulumi stack output sns_error_topic_arn
pulumi stack output sns_billing_topic_arn  # If billing alerts enabled
```

**Verification:**
```bash
# List subscriptions
aws sns list-subscriptions

# Test by publishing a message
aws sns publish \
  --topic-arn $(pulumi stack output sns_info_warning_topic_arn) \
  --message "Test message"
```

---

### 6. Review Service Quotas

**Purpose:** Ensure your AWS account has sufficient quotas for your expected load.

**Steps:**

- [ ] **Review Amazon Connect Quotas**
  - Concurrent calls per instance
  - Concurrent chats per instance
  - Contact flows per instance
  - Phone numbers per instance

- [ ] **Request Quota Increases (if needed)**
  - Submit requests through AWS Service Quotas console
  - ⚠️ Some increases can take several days

**📚 Reference:** [Amazon Connect Service Quotas](https://docs.aws.amazon.com/connect/latest/adminguide/amazon-connect-service-limits.html)

**Check Current Quotas:**
```bash
# List current quotas
aws service-quotas list-service-quotas \
  --service-code connect \
  --region $(pulumi config get aws:region)
```

---

### 7. Enable Outbound Campaigns (Optional)

**Purpose:** Required if you plan to use outbound calling campaigns.

**Steps:**

- [ ] **Enable in AWS Console**
  - This feature must be enabled via AWS Console
  - No API is currently available
  - Contact AWS Support if needed

**📚 Reference:** [Amazon Connect Outbound Campaigns](https://docs.aws.amazon.com/connect/latest/adminguide/outbound-campaigns.html)

---

## 🎯 Completion Checklist

Use this to track your overall progress:

### Core Setup (Required)
- [ ] Contact flow features enabled
- [ ] SNS subscriptions confirmed

### Authentication (If applicable)
- [ ] SAML configured (if using SAML authentication)
- [ ] Users assigned in IdP
- [ ] Login tested

### Features (If enabled)
- [ ] Customer Profiles domain associated
- [ ] Amazon Q knowledge base populated
- [ ] Service quotas reviewed
- [ ] Outbound campaigns enabled (if needed)

---

## 🔍 Verification Commands

Run these commands to verify your deployment:

```bash
# Check all Pulumi outputs
pulumi stack output

# List all created S3 buckets
aws s3 ls | grep -E 'connect|elevai'

# Check Connect instance status
aws connect describe-instance \
  --instance-id $(pulumi stack output connect_instance_id)

# List all Parameter Store parameters created
aws ssm get-parameters-by-path \
  --path /elevai \
  --recursive

# Check CloudWatch alarms
aws cloudwatch describe-alarms \
  --alarm-name-prefix connect

# List SNS topics
aws sns list-topics | grep elevai
```

---

## 📚 Additional Resources

- **Main README:** [README.md](../README.md)
- **SAML Setup:** [docs/SAML_SETUP_GUIDE.md](SAML_SETUP_GUIDE.md)
- **Customer Profiles:** [docs/CUSTOMER_PROFILES.md](CUSTOMER_PROFILES.md)
- **Amazon Q Setup:** [docs/AMAZON_Q_SETUP.md](AMAZON_Q_SETUP.md)
- **Monitoring Guide:** [docs/MONITORING_GUIDE.md](MONITORING_GUIDE.md)
- **Custom Extensions:** [docs/CUSTOM_EXTENSIONS_GUIDE.md](CUSTOM_EXTENSIONS_GUIDE.md)

---

## ❓ Need Help?

If you encounter issues:

1. **Check Pulumi logs:** `pulumi logs`
2. **Review stack outputs:** `pulumi stack output`
3. **Verify AWS resources in Console**
4. **Check documentation for specific features**
5. **Open an issue:** [GitHub Issues](https://github.com/bloy.me.uk/elevai-connect/issues)

---

## 📝 Notes Section

Use this space to track deployment-specific notes:

```
Deployment Date: _______________
Stack Name: _______________
AWS Region: _______________
Instance Alias: _______________

Custom Notes:
- 
- 
- 
```

---

**Last Updated:** 2025-01-XX
**Version:** 1.0.0
