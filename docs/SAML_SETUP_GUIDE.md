# SAML Setup Guide for Amazon Connect

This guide covers everything you need to configure SAML 2.0 authentication for your Amazon Connect instance, including deployment, post-deployment configuration, and troubleshooting.

---

## 🎯 Overview

SAML (Security Assertion Markup Language) 2.0 allows you to integrate Amazon Connect with your existing identity provider (IdP) for Single Sign-On (SSO). This means users authenticate with your corporate identity system and gain access to Amazon Connect without separate credentials.

**Benefits:**
- 🔐 Centralized user management
- 🔄 Automatic provisioning and deprovisioning
- 📊 Enhanced security and compliance
- 🎯 Single Sign-On experience for users

**Supported Identity Providers:**
- Okta
- Azure Active Directory (Azure AD)
- Google Workspace
- Any SAML 2.0 compatible IdP

---

## ✅ Prerequisites

Before configuring SAML, ensure you have:

- [ ] Access to your Identity Provider (IdP) administration console
- [ ] Ability to create SAML applications in your IdP
- [ ] AWS account with permissions to create Amazon Connect instances
- [ ] Downloaded SAML metadata XML file from your IdP (or ability to retrieve it)
- [ ] Understanding of your organization's user directory structure

---

## 🚀 Initial Deployment

### Step 1: Configure SAML in Pulumi

Edit your `Pulumi.dev.yaml` file:

```yaml
config:
  # Set identity management type to SAML
  connect:identityManagementType: SAML
  
  # Optional: Provide your IdP metadata file path
  # If not provided, you'll configure this post-deployment
  connect:samlMetadataFile: "./path/to/saml-metadata.xml"
  
  # Other required settings
  connect:instanceAlias: your-unique-alias
  aws:region: us-east-1
```

⚠️ **Important:** 
- `identityManagementType` is **permanent** and cannot be changed after instance creation
- Choose carefully between `SAML` and `CONNECT_MANAGED`
- The instance alias must be globally unique across all AWS accounts

### Step 2: Deploy Infrastructure

```bash
# Preview changes
pulumi preview

# Deploy
pulumi up

# Note the outputs - you'll need these for IdP configuration
pulumi stack output
```

**Key Outputs You'll Need:**
- `connect_instance_arn` - Your Connect instance ARN
- `connect_instance_id` - Your Connect instance ID
- `saml_provider_arn` - ARN of the IAM SAML provider (if metadata was provided)

---

## 🔧 Identity Provider Configuration

Follow the [Amazon Connect SSO Setup Workshop](https://catalog.us-east-1.prod.workshops.aws/workshops/33e6d0e7-f927-4531-abb1-f28a86ba0872/)


## 🎯 Best Practices

### Security

- ✅ Use group-based assignments in your IdP
- ✅ Implement least-privilege security profiles
- ✅ Enable MFA in your identity provider
- ✅ Regularly review and audit user access
- ✅ Rotate SAML certificates before expiration
- ✅ Use separate security profiles for different roles

### Operational

- 📋 Document your SAML configuration
- 📋 Keep metadata files in version control (sanitized)
- 📋 Test SAML changes in dev environment first
- 📋 Monitor login failures and authentication metrics
- 📋 Have a backup admin user (non-SAML) for emergencies
- 📋 Set up alerts for authentication failures

### User Management

- 👥 Use meaningful group names in IdP
- 👥 Map groups to Connect security profiles
- 👥 Automate user provisioning where possible
- 👥 Document security profile assignments
- 👥 Regularly review user access and permissions

---

## 📚 Additional Resources

- [AWS Amazon Connect SAML Documentation](https://docs.aws.amazon.com/connect/latest/adminguide/configure-saml.html)
- [SAML 2.0 Technical Overview](https://docs.oasis-open.org/security/saml/Post2.0/sstc-saml-tech-overview-2.0.html)
- [Okta Amazon Connect Integration Guide](https://saml-doc.okta.com/SAML_Docs/How-to-Configure-SAML-2.0-for-Amazon-Connect.html)
- [Azure AD SAML Configuration](https://docs.microsoft.com/en-us/azure/active-directory/saas-apps/)

