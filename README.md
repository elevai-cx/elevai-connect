# Amazon Connect Infrastructure

**Production-ready Amazon Connect infrastructure as code with pre-configured integrations, operational and security best practices.**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Pulumi](https://img.shields.io/badge/Pulumi-3.x-blueviolet)](https://www.pulumi.com/)
[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)
![CodeQL](https://github.com/DanBloy/elevai-connect/workflows/CodeQL/badge.svg)

A comprehensive, project for deploying Amazon Connect contact centers with Python. This project goes beyond basic infrastructure deployment to provide a battle-tested foundation with production-ready monitoring, intelligent alerting, SAML authentication, and additional out of the box features.

## PREVIEW: Deploy with Claude Code and MCP
AI has turned ideas into reality and with elevai-connect and MCP we re-imagine the developer experience. By using Claude Code you are able to interact using natural language to set-up and configure your Amazon Connect instance.

Once you have your instance, you will find workshops within this project that AI can walk you through to build great experiences and supercharge your development.

To get started visit the [README](/docs/CLAUDE_CODE_SETUP.md).

## Architecture overview

![](/elevai-connect.drawio.png)

## Features

This project aims to provide a core set of Amazon Connect features that can then be extended in 3 ways.

1. By using the ARNs provided in Parameter Store to any IaC of your choosing
2. By using the ./custom folder to develop customer features via Pulumi
3. Through additional modules that will be developed over time.

The current features available in this version are detailed below. These gaps can be configured as you see fit (Console / IaC), the gaps will be resolved over time when the resource can be configured via IaC (See an improvement? Why not [Contribute](CONTRIBUTING.md))

| Feature                              | Included |
| ------------------------------------ | -------- |
| Amazon Connect Instance              | ✅        |
| Amazon Q                             | ✅        |
| Customer Profiles                    | ✅        |
| **Storage Configuration**            |          |
| • Call recordings                    | ✅        |
| • Chat transcripts                   | ✅        |
| • Exported reports                   | ✅        |
| • Attachments                        | ✅        |
| • Screen recordings                  | ✅        |
| • Contact evaluations                | ✅        |
| • Email messages                     | ✅        |
| • Live media streaming               | ✅        |
| **Data Streaming**                   |          |
| • Agent Trace                        | ✅        |
| • Contact Records                    | ✅        |
| Data Lake with Athena                | ✅        |
| Approved origins                     | ✅        |
| Forecasting, Capacity and Scheduling | ✅        |
| Email Domain                         | ❌        |
| Outbound Campaign                    | ❌        |
| Tasks Integrations                   | ❌        |
| Cases                                | ❌        |
| External voice connector             | ❌        |
| Traffic Distribution (Multi-region)  | ❌        |

## 💡 Why This Project Exists

Amazon Connect is a powerful cloud contact center (CCaaS) platform that lives within your AWS account. However, deploying Connect in production requires integrating numerous AWS services - S3, DynamoDB, Lambda, CloudWatch, IAM, Secrets Manager, and more.

**The Problem:** While there's plenty of scattered example code and point solutions available across documentation, blogs, and forums, there's no comprehensive, production-ready solution that brings it all together. Teams typically spend weeks or months:

- Piecing together infrastructure from multiple sources
- Building monitoring and alerting from scratch
- Implementing security best practices through trial and error
- Creating custom integrations for each AWS service
- Learning hard lessons about what works (and what doesn't) in production

**The Solution:** This project consolidates real-world experience and best practices into a single, cohesive infrastructure-as-code solution. Instead of starting from scratch or stitching together fragmented examples, you get a battle-tested foundation that's production-ready from day one.

💪 **We've done the heavy lifting so you don't have to.** Deploy enterprise-grade Amazon Connect infrastructure in minutes, not months.


## ⚡ Quick Highlights

- ⏱️ **Deploy in minutes** - Simple YAML configuration, no complex coding required
- 🏗️ **Complete infrastructure** - Amazon Connect, S3, KMS, Kinesis, Analytics data lake, and more
- 🔐 **Enterprise SSO ready** - SAML 2.0 integration with your identity provider
- 🤖 **AI-powered** - Amazon Q in Connect with automated document tagging and session management
- 📊 **70+ monitoring alarms** - Proactive alerting for capacity, quality, and cost management
- 🔧 **Easily extensible** - Two flexible approaches:
  - Custom Pulumi modules in the `/custom` folder
  - Integration via AWS Systems Manager Parameter Store

## 👥 Who This Is For

This project is ideal for:

### 🏢 Small to Medium Businesses (SMBs)
- **Rapid deployment** - Launch a professional contact center without a large DevOps team
- **Cost-effective** - Built-in budget alerts and cost monitoring prevent surprise bills
- **Scalable** - Grow from a handful of agents to hundreds without infrastructure changes
- **Professional grade** - Get enterprise features without enterprise complexity

### 🤝 AWS Partners & Consultants
- **Accelerate client projects** - Deploy production-ready infrastructure in hours, not weeks
- **Consistent quality** - Deliver the same high standard across all client engagements
- **Customizable foundation** - Easy to extend and tailor for specific client requirements
- **Best practices included** - Security, monitoring, and compliance built-in from day one
- **Competitive advantage** - Differentiate with rapid, reliable deployments

### 🚀 Startups & Scale-ups
- **Focus on your product** - Spend time on customer experience, not infrastructure
- **Production-ready from day one** - No need to retrofit monitoring and security later
- **Grow with confidence** - Comprehensive alerting catches issues before customers do

### 🏗️ DevOps & Platform Teams
- **Infrastructure as Code** - Version controlled, repeatable, auditable deployments
- **Modular architecture** - Extend without modifying core components
- **Clear separation** - Core vs. custom resources keeps updates clean

## 🗺️ Roadmap

- 📧 **Voicemail** - AWS voicemail functionality 
- 📞 **Contact Flow Templates** - Pre-built flows for common use cases
- 🔒 **Compliance Contact Recording** - Extend Amazon Connect search and playback beyond 2 years for regulatory requirements

**Want to influence the roadmap?** Open an issue or start a discussion in our GitHub repository!

## ✨ Feature Details

### 🏗️ **Production-Ready Infrastructure**
- Complete Amazon Connect instance setup with all core resources
- S3 buckets with intelligent lifecycle policies and compliance-friendly retention
- Lambda functions for common use cases and Amazon Q knowledgebase

### 📊 **Enterprise Monitoring & Alerting**
- **70+ CloudWatch alarms** covering all critical metrics
- Multi-tier alerting (INFO/WARNING/ERROR) with SNS integration
- Proactive capacity monitoring (concurrent calls, chats, emails, tasks)
- Call quality alerts (packet loss, missed calls, throttling)
- Cost protection with AWS Budget alerts and threshold notifications
- Customizable alarm thresholds per environment (dev/staging/prod)

### 🤖 **AI-Powered Agent Assistance**
- **Amazon Q in Connect** integration for intelligent agent support
- Knowledge base management with automated content tagging
- Real-time suggestions during customer interactions
- Folder-based content organization with metadata tagging

### 📊 **Analytics Data Lake**
- **Automated data lake setup** with AWS Lake Formation integration
- **27 pre-configured resource links** to Amazon Connect analytics tables
- **Auto-discovery** of shared databases via AWS RAM (Resource Access Manager)
- **Athena workgroup** pre-configured for querying contact center data
- **Idempotent deployments** - safe to run multiple times without errors
- Query historical data including:
  - Contact records and evaluations
  - Agent statistics and performance metrics
  - Queue metrics and routing profiles
  - Contact Lens conversational analytics
  - Bot conversations and intents
  - Workforce management data (shifts, forecasts, schedules)
- See the [Analytics Data Lake Guide](docs/ANALYTICS_DATA_LAKE.md) for detailed setup and query examples

### 🔐 **Security & Compliance**
- SAML 2.0 authentication with external IdP integration (Okta, Azure AD, Google)
- Encryption at rest and in transit for all data stores
- Audit logging with CloudWatch and S3 integration
- Configurable data retention for compliance (GDPR, SOC2, PCI)

### 🔧 **Developer-Friendly**
- Modular architecture separating core infrastructure from customizations
- Zero-downtime updates to core modules
- Extensive configuration options via Pulumi stack configs
- Comprehensive documentation and examples

## 🚀 Quick Start

### Prerequisites

- **Python 3.13+** installed
- **[Pulumi CLI](https://www.pulumi.com/docs/get-started/install/)** installed
- **AWS CLI** configured with appropriate credentials
- AWS account with permissions for Amazon Connect, IAM, S3, DynamoDB, Lambda


### Installation

```bash
# 1. Clone the repository
git clone https://github.com/bloy.me.uk/elevai-connect.git
cd elevai-connect

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure Pulumi
pulumi login --local # Use Pulumi Cloud or local backend. S3 can be used: https://www.pulumi.com/docs/iac/concepts/state-and-backends/#using-a-diy-backend

# 5. Set up your configuration file
cp Pulumi.dev.yaml.example Pulumi.dev.yaml
pulumi stack init dev
```

**Important**: Edit `Pulumi.dev.yaml` and customize these critical settings:

```yaml
# 1. Your AWS region
aws:region: eu-west-2                        # Change to your region

# 2. Email addresses for alerts
alerting:error_email: "your-email@example.com"
billing:notificationEmail: "your-email@example.com"

# 3. Unique Amazon Connect instance alias (CANNOT BE CHANGED LATER!)
connect:instanceAlias: your-unique-alias      # Must be globally unique

# 4. Identity management type (CANNOT BE CHANGED LATER!)
connect:identityManagementType: SAML          # Options: SAML or CONNECT_MANAGED

# 6. Save you SAML Metadata file in the path below (OPTIONAL - can be updated post deployment)
connect:samlMetadataFile:  "./path/to/saml/metadata.xml"

# 6. Monthly budget limit (For email alerts)
billing:monthlyBudgetLimit: "50"              # USD


```

> ⚠️ **Warning**: `instanceAlias` and `identityManagementType` are **permanent** - they cannot be changed after the Connect instance is created. Choose carefully!

### Deploy

```bash
# Preview infrastructure changes
pulumi preview

# Deploy to AWS
pulumi up

# View created resources
pulumi stack output
```

### Post-Deployment Manual Steps

Due to AWS API limitations, complete these steps manually:

Open up AWS Console > Amazon Connect > Your instance > Flows

1. **[Enable Automated Interaction Logs](https://docs.aws.amazon.com/connect/latest/adminguide/monitor-automated-interaction-logs.html)**
2. **[Enable Lex Bot Management & Analytics](https://docs.aws.amazon.com/connect/latest/adminguide/enable-bot-building.html)**
3. **Verify Next Generation Amazon Connect** is enabled (default for new instances)

**For SAML authentication setup**, see the comprehensive [SAML Configuration Guide](docs/SAML_SETUP_GUIDE.md) which covers:
- Identity Provider configuration (Okta, Azure AD, Google Workspace)
- Post-deployment SAML setup
- User assignment and permissions
- Complete troubleshooting guide


## ⚙️ Configuration

### Understanding Pulumi Configuration Files

This project uses two types of configuration files:

| File              | Purpose             | Committed to Git? | Contains                               |
| ----------------- | ------------------- | ----------------- | -------------------------------------- |
| `Pulumi.yaml`     | Project definition  | ✅ Yes             | Project name, runtime, description     |
| `Pulumi.dev.yaml` | Stack configuration | 🚫 No              | AWS regions, emails, instance settings |

**Key Points:**
- **`Pulumi.yaml`** - The same for all users (defines the project)
- **`Pulumi.<stack>.yaml`** - Different for each environment (dev, staging, prod) and user
- Stack files contain personal/sensitive data and should **never** be committed
- Use `Pulumi.dev.yaml.example` as a template to create your own stack configuration

### Configuration for Multiple Environments

Create separate configuration files for different environments:

```bash
# Development
cp Pulumi.dev.yaml.example Pulumi.dev.yaml
# Edit: Higher alarm thresholds, test emails, smaller budget

# Production
cp Pulumi.dev.yaml.example Pulumi.prod.yaml
# Edit: Stricter thresholds, ops team emails, production budget
```

Switch between environments:

```bash
pulumi stack select dev
pulumi up

pulumi stack select prod
pulumi up
```

### Core Settings

Configuration is managed through Pulumi stack files (e.g., `Pulumi.dev.yaml`). The project includes extensive configuration options:



## 🚀 Moving to Production

### Pre-Production Checklist

Before going live with your Amazon Connect instance:

#### 1. Review Service Quotas

Post deployment, review the [Service Quotas for Amazon Connect](https://docs.aws.amazon.com/connect/latest/adminguide/amazon-connect-service-limits.html#important-quota-info). 

⚠️ **Important:** Some quota increases can take several days to be approved. Plan accordingly!

**Key quotas to review:**
- Concurrent active calls per instance
- Concurrent active chats per instance
- Contact flows per instance
- Hours of operation
- Queues per instance
- Phone numbers per instance
- Outbound country calling
- Outbound custom CLIs


#### 3. Monitoring & Alerting

- [ ] Verify SNS email subscriptions

#### 4. Disaster Recovery

- [ ] Document recovery procedures
- [ ] Test backup and restore processes
- [ ] Verify data retention policies
- [ ] Plan for cross-region failover (if needed)

#### 5. User Acceptance Testing

- [ ] Test all contact flows end-to-end
- [ ] Verify SAML authentication (if applicable)
- [ ] Test agent experience
- [ ] Validate integrations

## 📊 Monitoring & Alerting

For more details visit the [Monitoring Guide](docs/MONITORING_GUIDE.md)

### Multi-Tier Alert System

- **ERROR alerts** → Critical issues requiring immediate action
- **INFO/WARNING alerts** → Important notifications and trends
- Separate SNS topics for alert routing
- Email notifications (customizable per environment)

### Coverage Areas

**Amazon Connect Metrics:**
- Concurrent capacity (calls, chats, emails, tasks) - WARNING at 70%, ERROR at 85%
- Call quality (packet loss, missed calls, throttling)
- Operational issues (flow errors, recording failures, queue overflow)

**Lambda Functions:**
- Error rates and throttling
- Duration and timeout warnings
- Concurrent execution limits

**SQS Dead Letter Queues:**
- Message count and age monitoring
- Failed message processing alerts

**Cost Management:**
- AWS Budget with configurable thresholds
- Multi-tier budget alerts (50%, 80%, 100%)

For detailed alarm documentation, see:
- [Monitoring Guide](docs/MONITORING_GUIDE.md)



## 🔒 Security & Compliance

**Compliance Standards:**

This project is checked for compliance against:
- ✅ CIS AWS Foundations Benchmark v1.2.0
- ✅ PCI DSS v4.0.1
- ✅ AWS Foundational Security Best Practices v1.0.0
- ✅ AWS Resource Tagging Standard v1.0.0

See [SECURITY.md](SECURITY.md) for vulnerability reporting and detailed security documentation.

### Built-in Security Features

- **Encryption**: All S3 buckets and DynamoDB tables encrypted at rest
- **IAM Policies**: Least-privilege access for all resources
- **Network Security**: VPC integration ready (optional)
- **Audit Logging**: CloudWatch Logs for all operations
- **Secrets Management**: AWS Secrets Manager integration
- **SAML Authentication**: Enterprise SSO support

### Data Retention & Compliance

Configurable lifecycle policies for compliance requirements:

```yaml
# Example: 7-year retention for call recordings (compliance)
s3:recordings.archiveDays: "90"     # Move to Glacier after 90 days
s3:recordings.deletionDays: "2555"   # Delete after 7 years
```

For a complete security review checklist, see the [Moving to Production](#-moving-to-production) section.

## 🎨 Custom Extensions

The `custom/` directory is designed for your organization-specific extensions and won't conflict with core updates.

**Two flexible integration approaches:**


1. [Custom Extensions Guide](docs/CUSTOM_EXTENSIONS_GUIDE.md) - Add AWS resources managed by Pulumi
   - Lambda functions for integrations
   - Additional DynamoDB tables
   - API Gateways for webhooks
   - Any AWS resource you need

2. [Parameter Store Guide](docs/MONITORING_GUIDE.md) - Export core resource ARNs for external systems
   - Connect instance details
   - S3 bucket names
   - Q Assistant IDs
   - Available to any application via AWS Systems Manager


## Known limitations

### Outbound Campaigns
This needs to be enabled via the AWS Console due to no API being currently available for this.


## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.


## 📖 Documentation

**📂 [Browse All Documentation Guides](docs/README.md)**

### Project Guides

- 🔒 **[SECURITY.md](SECURITY.md)** - Security policy and vulnerability reporting
- 📘 **[SAML Setup Guide](docs/SAML_SETUP_GUIDE.md)** - Complete SAML authentication configuration
- 🤖 **[Amazon Q Setup Guide](docs/AMAZON_Q_SETUP.md)** - AI assistant configuration and management
- 📊 **[Analytics Data Lake Guide](docs/ANALYTICS_DATA_LAKE.md)** - Query contact center data with SQL
- 🔧 **[Custom Extensions Guide](docs/CUSTOM_EXTENSIONS_GUIDE.md)** - Extending with custom resources
- 🔧 **[Parameter Store Guide](docs/PARAMETER_STORE_GUIDE.md)** - Extending with custom resources
- 📊 **[Monitoring Guide](docs/MONITORING_GUIDE.md)** - CloudWatch alarms detailed setup
- 🤝 **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines

### External Resources

- [Pulumi AWS Documentation](https://www.pulumi.com/docs/clouds/aws/)
- [Amazon Connect Documentation](https://docs.aws.amazon.com/connect/)
- [Amazon Q in Connect](https://docs.aws.amazon.com/connect/latest/adminguide/amazon-q-connect.html)
- [Pulumi Python SDK](https://www.pulumi.com/docs/languages-sdks/python/)


## 🔄 Version History

See [CHANGELOG.md](CHANGELOG.md) for version history and release notes.

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2025 ELEVAI

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

## 👥 Support & Community

- **Issues**: [GitHub Issues](https://github.com/bloy.me.uk/elevai-connect/issues)
- **Discussions**: [GitHub Discussions](https://github.com/bloy.me.uk/elevai-connect/discussions)

## 🌟 Acknowledgments

Built with ❤️ by ELEVAI using:
- [Pulumi](https://www.pulumi.com/) - Modern Infrastructure as Code
- [AWS](https://aws.amazon.com/) - Cloud Infrastructure
- [Amazon Connect](https://aws.amazon.com/connect/) - Contact Center Platform

---

**Ready to deploy world-class contact center infrastructure?** Get started in minutes with production-ready monitoring, AI assistance, and security built-in.


# Deleting the stack

1. Empty all S3 buckets
2. Athena Workgroup needs to be manually deleted? (TODO)
3. Delete any LEX bots created via the AWS Console
4. Run `pulumi destroy`