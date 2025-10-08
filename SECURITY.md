# Security Policy

## Compliance Standards

This project has been checked for compliance against the following security standards, for the resources it deploys:

- **CIS AWS Foundations Benchmark v1.2.0**
- **PCI DSS v4.0.1**
- **AWS Foundational Security Best Practices v1.0.0**
- **AWS Resource Tagging Standard v1.0.0**

## Security Features

### Built-in Protection

- 🔐 **Encryption at Rest**: All S3 buckets and DynamoDB tables use AWS KMS encryption
- 🔒 **Encryption in Transit**: TLS 1.2+ enforced for all communications
- 👤 **IAM Least Privilege**: Role-based access with minimal required permissions
- 📊 **Audit Logging**: CloudWatch and CloudTrail integration for all actions
- 🔑 **Secrets Management**: AWS Secrets Manager for sensitive data
- 🛡️ **Network Security**: VPC integration ready with security group controls

### Monitoring & Detection

- 70+ CloudWatch alarms for anomaly detection
- Real-time alerting for security events
- Budget monitoring to detect unauthorized resource usage
- Failed authentication tracking

# S3 Server Access Logging Configuration

## Overview
All Amazon Connect S3 buckets have server access logging enabled, sending logs to a centralized logging bucket.

## Bucket Structure

### Amazon Connect Data Buckets (ALL have logging enabled):
1. **call-recordings** → logs to `s3-access-logs/call-recordings/`
2. **chat-transcripts** → logs to `s3-access-logs/chat-transcripts/`
3. **exported-reports** → logs to `s3-access-logs/exported-reports/`
4. **attachments** → logs to `s3-access-logs/attachments/`
5. **screen-recordings** → logs to `s3-access-logs/screen-recordings/`
6. **contact-evaluations** → logs to `s3-access-logs/contact-evaluations/`
7. **email-messages** → logs to `s3-access-logs/email-messages/`
8. **q-knowledge-bucket** → logs to `s3-access-logs/q-knowledge-bucket/`
9. **connect-logs-bucket** (Kinesis Firehose) → logs to `s3-access-logs/connect-logs-bucket/`

### Centralized Logging Bucket:
- **s3-access-logs** - Receives all access logs from the above buckets
  - **Does NOT have logging enabled on itself** (AWS best practice)
  - Has KMS encryption enabled
  - Has versioning enabled
  - Has lifecycle policies (90 days → IA, 365 days → expire)

## Security Control: "S3 general purpose buckets should have server access logging enabled"

### ✅ COMPLIANT (All Amazon Connect buckets):
All 9 Amazon Connect data buckets have server access logging enabled and will pass the security control.

### ⚠️ EXPECTED FINDING (Logging bucket only):
The `s3-access-logs` bucket itself will show this finding. This is **EXPECTED and correct** because:

1. **AWS Best Practice**: Logging buckets should NOT have logging enabled to avoid:
   - Infinite logging loops (logs generating more logs)
   - Exponential storage cost growth
   - Management complexity

2. **Security Posture**: The logging bucket still has:
   - ✅ KMS encryption (customer-managed key)
   - ✅ Versioning enabled
   - ✅ Public access blocked
   - ✅ SSL/TLS required
   - ✅ Lifecycle policies configured

## Recommended Action

**Suppress/exempt the security finding for the `s3-access-logs` bucket only.**

In AWS Security Hub or your compliance tool:
1. Find the finding for `s3-access-logs` bucket
2. Create a suppression rule with justification: "Logging bucket - AWS best practice to not enable logging to avoid infinite loops"
3. All other buckets should pass the control

## Reporting a Vulnerability

Via [GitHub security](https://github.com/DanBloy/elevai-connect/security/policy)

## Compliance Resources

- [CIS AWS Foundations Benchmark](https://www.cisecurity.org/benchmark/amazon_web_services)
- [PCI DSS Requirements](https://www.pcisecuritystandards.org/)
- [AWS Security Best Practices](https://aws.amazon.com/architecture/security-identity-compliance/)
- [Amazon Connect Security](https://docs.aws.amazon.com/connect/latest/adminguide/security.html)

## Staying Secure

- Subscribe to [AWS Security Bulletins](https://aws.amazon.com/security/security-bulletins/)
- Monitor [GitHub Security Advisories](https://github.com/bloy.me.uk/elevai-connect/security/advisories)
- Review CHANGELOG for security-related updates
- Keep Pulumi and dependencies up to date

## Questions?

For security questions that are not vulnerabilities, open a GitHub issue or discussion.

---

**Last Updated**: 2025-10-07
