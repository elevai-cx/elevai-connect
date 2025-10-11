# Documentation

Welcome to the Amazon Connect Infrastructure documentation! This directory contains comprehensive guides for all features and capabilities.

## 📚 Available Guides

### Getting Started

- **[Main README](../README.md)** - Project overview, quick start, and configuration
- **[POST_DEPLOYMENT_STEPS.md](POST_DEPLOYMENT_STEPS.md)** - Consolidated checklist of all manual configuration steps
- **[CLAUDE_CODE_SETUP.md](CLAUDE_CODE_SETUP.md)** - Deploy using AI with Claude Code and MCP

### Core Features

- **[SAML_SETUP_GUIDE.md](SAML_SETUP_GUIDE.md)** - Enterprise SSO configuration
  - Okta, Azure AD, and Google Workspace integration
  - Post-deployment setup steps
  - Troubleshooting and testing

- **[AMAZON_Q_GUIDE.md](AMAZON_Q_GUIDE.md)** - AI-powered agent assistance
  - Knowledge base setup and management
  - Automated content tagging
  - Session management

- **[ANALYTICS_DATA_LAKE.md](ANALYTICS_DATA_LAKE.md)** - Query contact center data with SQL
  - 27 pre-configured analytics tables
  - Example SQL queries for common reports
  - Integration with BI tools (QuickSight, Tableau, Power BI)
  - Performance optimization and best practices

### Monitoring & Operations

- **[MONITORING_GUIDE.md](MONITORING_GUIDE.md)** - CloudWatch alarms and alerting
  - 70+ pre-configured alarms
  - Multi-tier alert system (ERROR/WARNING/INFO)
  - Capacity, quality, and cost monitoring

### Customization & Extension

- **[CUSTOM_EXTENSIONS_GUIDE.md](CUSTOM_EXTENSIONS_GUIDE.md)** - Add custom AWS resources
  - Lambda functions for integrations
  - Additional DynamoDB tables
  - API Gateways for webhooks

- **[PARAMETER_STORE_GUIDE.md](PARAMETER_STORE_GUIDE.md)** - Export resource ARNs
  - Connect instance details
  - S3 bucket names
  - Integration with external systems

### Security & Compliance

- **[../SECURITY.md](../SECURITY.md)** - Security policy and vulnerability reporting
  - Compliance standards (CIS, PCI DSS, AWS Best Practices)
  - Built-in security features
  - Vulnerability reporting process

### Contributing

- **[../CONTRIBUTING.md](../CONTRIBUTING.md)** - How to contribute to this project
  - Code of conduct
  - Development workflow
  - Pull request guidelines

## 🎯 Quick Links by Use Case

### "I just deployed - what manual steps do I need to complete?"
→ [POST_DEPLOYMENT_STEPS.md](POST_DEPLOYMENT_STEPS.md)

### "I want to enable SSO login"
→ [SAML_SETUP_GUIDE.md](SAML_SETUP_GUIDE.md)

### "I want to add AI agent assistance"
→ [AMAZON_Q_GUIDE.md](AMAZON_Q_GUIDE.md)

### "I want to query historical contact data"
→ [ANALYTICS_DATA_LAKE.md](ANALYTICS_DATA_LAKE.md)

### "I want to monitor my contact center"
→ [MONITORING_GUIDE.md](MONITORING_GUIDE.md)

### "I want to add custom Lambda functions"
→ [CUSTOM_EXTENSIONS_GUIDE.md](CUSTOM_EXTENSIONS_GUIDE.md)

### "I want to integrate with external systems"
→ [PARAMETER_STORE_GUIDE.md](PARAMETER_STORE_GUIDE.md)

### "I want to deploy using AI"
→ [CLAUDE_CODE_SETUP.md](CLAUDE_CODE_SETUP.md)

## 📖 Documentation Standards

All guides in this directory follow these principles:

- ✅ **Step-by-step instructions** - Clear, actionable steps
- ✅ **Real-world examples** - Practical code samples and screenshots
- ✅ **Troubleshooting sections** - Common issues and solutions
- ✅ **Best practices** - Production-ready recommendations
- ✅ **External links** - References to official AWS documentation

## 🆘 Need Help?

If you can't find what you're looking for:

1. **Search the docs** - Use GitHub's search or `Ctrl/Cmd + F`
2. **Check GitHub Issues** - Someone may have asked the same question
3. **Start a Discussion** - Ask the community
4. **Open an Issue** - Report bugs or documentation gaps

## 📝 Contributing to Documentation

Found a typo? Have a suggestion? Want to add an example?

We welcome documentation improvements! See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

---

**👈 Back to [Main README](../README.md)**
