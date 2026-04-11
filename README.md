# Amazon Connect Infrastructure

**Production-ready Amazon Connect infrastructure as code with pre-configured integrations, operational and security best practices.**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Pulumi](https://img.shields.io/badge/Pulumi-3.x-blueviolet)](https://www.pulumi.com/)
[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)
![CodeQL](https://github.com/elevai-cx/elevai-connect/workflows/CodeQL/badge.svg)

A comprehensive project for deploying Amazon Connect contact centers with Python. This project goes beyond basic infrastructure deployment to provide a battle-tested foundation with production-ready monitoring, intelligent alerting, SAML authentication, and additional out of the box features.

> **New here?** Follow the **[Getting Started guide](docs/GETTING_STARTED.md)** to deploy your first instance in 15-20 minutes.

## Architecture overview

![](/elevai-connect.drawio.png)

## Features

This project aims to provide a core set of Amazon Connect features that can then be extended in 3 ways.

1. By using the ARNs provided in Parameter Store to any IaC of your choosing
2. By using the ./custom folder to develop customer features via Pulumi
3. Through additional modules that will be developed over time.

The current features available in this version are detailed below. These gaps can be configured as you see fit (Console / IaC), the gaps will be resolved over time when the resource can be configured via IaC (See an improvement? Why not [Contribute](CONTRIBUTING.md))

| Feature                              | Included        |
| ------------------------------------ | --------------- |
| Amazon Connect Instance              | ✅               |
| Amazon Q                             | ✅               |
| Customer Profiles                    | ✅               |
| Storage Configuration                |                 |
| • Call recordings                    | ✅               |
| • Chat transcripts                   | ✅               |
| • Exported reports                   | ✅               |
| • Attachments                        | ✅               |
| • Screen recordings                  | ✅               |
| • Contact evaluations                | ✅               |
| • Email messages                     | ✅               |
| • Live media streaming               | ✅               |
| Data Streaming                       |                 |
| • Agent Trace                        | ✅               |
| • Contact Records                    | ✅               |
| Data Lake with Athena                | ✅               |
| Approved origins                     | ✅               |
| Forecasting, Capacity and Scheduling | ✅               |
| Email Domain                         | Post Deployment |
| Outbound Campaign                    | Post Deployment |
| Cases                                | ✅               |

| Custom Integrations           | Included |
| ----------------------------- | -------- |
| Voicemail                     | ✅        |
| Business User Interface (BUI) | ✅        |

## 💡 Why This Project Exists

Amazon Connect is a powerful cloud contact center (CCaaS) platform that lives within your AWS account. However, deploying Connect in production requires integrating numerous AWS services - S3, DynamoDB, Lambda, CloudWatch, IAM, Secrets Manager, and more.

**The Problem:** While there's plenty of scattered example code and point solutions available across documentation, blogs, and forums, there's no comprehensive, production-ready solution that brings it all together. Teams typically spend weeks or months piecing together infrastructure from multiple sources, building monitoring from scratch, and implementing security best practices through trial and error.

**The Solution:** This project consolidates real-world experience and best practices into a single, cohesive infrastructure-as-code solution. Instead of starting from scratch or stitching together fragmented examples, you get a battle-tested foundation that's production-ready from day one.

## ⚡ Quick Highlights

- ⏱️ **Deploy in minutes** - Simple YAML configuration, no complex coding required
- 🏗️ **Complete infrastructure** - Amazon Connect, S3, KMS, Kinesis, Analytics data lake, and more
- 🔐 **Enterprise SSO ready** - SAML 2.0 integration with your identity provider
- 🤖 **AI-powered** - Amazon Q in Connect with automated document tagging and session management
- 📊 **70+ monitoring alarms** - Proactive alerting for capacity, quality, and cost management
- 🎛️ **Business User Interface** - Admin UI Workspaces and Data Tables for operational control without code changes
- 🔧 **Easily extensible** - Custom Pulumi modules in `/custom` or integration via AWS Systems Manager Parameter Store

## 👥 Who This Is For

### 🏢 Small to Medium Businesses (SMBs)
Launch a professional contact center without a large DevOps team. Built-in budget alerts and cost monitoring prevent surprise bills. Grow from a handful of agents to hundreds without infrastructure changes.

### 🤝 AWS Partners & Consultants
Accelerate client projects with production-ready infrastructure in hours. Consistent quality across engagements with a customizable foundation that's easy to extend and tailor.

### 🚀 Startups & Scale-ups
Focus on customer experience, not infrastructure. Production-ready from day one with comprehensive alerting that catches issues before customers do.

### 🏗️ DevOps & Platform Teams
Version controlled, repeatable, auditable deployments. Modular architecture with clear separation between core and custom resources keeps updates clean.

## 🗺️ Roadmap

- 📞 **Contact Flow Templates** - Pre-built flows for common use cases
- 🔒 **Compliance Contact Recording** - Extend Amazon Connect search and playback beyond 2 years for regulatory requirements

**Want to influence the roadmap?** Open an issue or start a discussion in our GitHub repository!

## 🔒 Security & Compliance

This project is checked for compliance against CIS AWS Foundations Benchmark v1.2.0, PCI DSS v4.0.1, AWS Foundational Security Best Practices v1.0.0, and AWS Resource Tagging Standard v1.0.0.

Built-in security features include encryption at rest for all data stores, least-privilege IAM policies, audit logging via CloudWatch, AWS Secrets Manager integration, SAML 2.0 authentication, and configurable data retention policies for GDPR, SOC2, and PCI compliance.

See [SECURITY.md](SECURITY.md) for vulnerability reporting and detailed security documentation.

## 🎨 Custom Extensions

The `custom/` directory is designed for your organization-specific extensions and won't conflict with core updates. Two flexible integration approaches:

1. [Custom Extensions Guide](docs/CUSTOM_EXTENSIONS_GUIDE.md) - Add AWS resources managed by Pulumi (Lambda functions, DynamoDB tables, API Gateways, and more)
2. [Parameter Store Guide](docs/PARAMETER_STORE_GUIDE.md) - Export core resource ARNs for use with external systems via AWS Systems Manager

## Known limitations

### Outbound Campaigns
This needs to be enabled via the AWS Console due to no API being currently available for this.

## 📖 Documentation

**📂 [Browse All Documentation Guides](docs/README.md)**

- 🚀 **[Getting Started](docs/GETTING_STARTED.md)** - Deploy your first instance step-by-step
- 📋 **[Post-Deployment Steps](docs/POST_DEPLOYMENT_STEPS.md)** - Manual steps after deployment
- 🔒 **[SECURITY.md](SECURITY.md)** - Security policy and vulnerability reporting
- 📘 **[SAML Setup Guide](docs/SAML_SETUP_GUIDE.md)** - Complete SAML authentication configuration
- 🤖 **[Amazon Q Guide](docs/AMAZON_Q_GUIDE.md)** - AI assistant configuration and management
- 📊 **[Analytics Data Lake Guide](docs/ANALYTICS_DATA_LAKE.md)** - Query contact center data with SQL
- 🔧 **[Custom Extensions Guide](docs/CUSTOM_EXTENSIONS_GUIDE.md)** - Extending with custom resources
- 🔧 **[Parameter Store Guide](docs/PARAMETER_STORE_GUIDE.md)** - Export resource ARNs for external systems
- 📊 **[Monitoring Guide](docs/MONITORING_GUIDE.md)** - CloudWatch alarms detailed setup (70+ alarms)
- 🎛️ **[BUI Guide](docs/BUI_GUIDE.md)** - Business User Interface setup and configuration
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

## 👥 Support & Community

- **Issues**: [GitHub Issues](https://github.com/elevai-cx/elevai-connect/issues)
- **Discussions**: [GitHub Discussions](https://github.com/elevai-cx/elevai-connect/discussions)

## 🌟 Acknowledgments

Built with ❤️ by ELEVAI using [Pulumi](https://www.pulumi.com/), [AWS](https://aws.amazon.com/), and [Amazon Connect](https://aws.amazon.com/connect/).

---

**Ready to get started?** Follow the **[Getting Started guide](docs/GETTING_STARTED.md)** to be up and running in minutes.
