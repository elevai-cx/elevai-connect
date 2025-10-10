# Custom Extensions Guide

This guide explains how to extend elevai-connect with your own custom resources while maintaining compatibility with core updates.

---

## 🎯 Overview

The `custom/` directory is specifically designed for your organization-specific extensions. This architecture ensures:

- ✅ **Zero conflicts** with core infrastructure updates
- ✅ **Easy upgrades** - pull core updates without breaking your customizations
- ✅ **Clean separation** - core vs. custom resources remain independent
- ✅ **Full access** - reference core resources in your custom code
- ✅ **Flexibility** - extend in any direction your business needs

**When to use custom extensions:**
- Organization-specific integrations
- Third-party API connections
- Custom Lambda functions
- Additional AWS resources
- Business logic implementations

---

## 🏗️ Architecture

### Directory Structure

```
elevai-connect/
├── core/                       # ⚠️ Don't modify (maintained by project)
│   ├── alerting/
│   ├── connect.py
│   ├── dynamodb.py
│   ├── lambda_functions.py
│   ├── s3.py
│   ├── iam.py
│   └── qconnect.py
├── custom/                     # ✅ Your extensions go here
│   ├── __init__.py
│   ├── README.md
│   ├── my_feature.py          # Your custom modules
│   └── integrations/          # Organize as needed
│       ├── salesforce.py
│       └── zendesk.py
└── __main__.py                 # Orchestrates core + custom
```

### How It Works

1. **Core infrastructure** deploys first (Connect, S3, IAM, etc.)
2. **Core resources** are passed to your custom modules
3. **Your custom code** references and extends core resources
4. **Everything deploys** together in a single `pulumi up`

### Core Resources Available

When you create custom resources, you have access to:

```python
core_resources = {
    "connect_instance": aws.connect.Instance,
    "s3": {
        "recordings": aws.s3.Bucket,
        "exports": aws.s3.Bucket,
        "knowledge_base": aws.s3.Bucket,
    },
    "dynamodb": {
        "contacts": aws.dynamodb.Table,
        "agents": aws.dynamodb.Table,
    },
    "iam": {
        "lambda_role": aws.iam.Role,
        "connect_role": aws.iam.Role,
    },
    "sns": {
        "error_topic": aws.sns.Topic,
        "info_warning_topic": aws.sns.Topic,
    },
    "qconnect": {
        "assistant": aws.connect.Assistant,
        "knowledge_base": aws.connect.KnowledgeBase,
    },
}
```

---

## 🚀 Getting Started

### Step 1: Create Your Custom Module

Create a new file in the `custom/` directory:

```bash
touch custom/my_feature.py
```

### Step 2: Basic Module Structure

```python
# custom/my_feature.py
import pulumi
import pulumi_aws as aws
from typing import Dict

def create_custom_resources(core_resources: Dict, tags: Dict) -> Dict:
    """
    Create custom resources for your organization.
    
    Args:
        core_resources: Dictionary of core infrastructure resources
        tags: Common tags to apply to all resources
        
    Returns:
        Dictionary of created custom resources
    """
    # Access core resources
    connect_instance = core_resources.get("connect_instance")
    recordings_bucket = core_resources["s3"]["recordings"]
    
    # Create your custom resources here
    custom_lambda = aws.lambda_.Function(
        "my-custom-function",
        runtime="python3.11",
        handler="index.handler",
        role=core_resources["iam"]["lambda_role"].arn,
        code=pulumi.AssetArchive({
            ".": pulumi.FileArchive("./lambda/my-function")
        }),
        environment={
            "variables": {
                "CONNECT_INSTANCE_ID": connect_instance.id,
                "RECORDINGS_BUCKET": recordings_bucket.id,
            }
        },
        tags=tags,
    )
    
    # Return your resources for reference
    return {
        "custom_lambda": custom_lambda,
    }
```

### Step 3: Register Your Module

Edit `custom/__init__.py` to import your module:

```python
# custom/__init__.py
from .my_feature import create_custom_resources

__all__ = ["create_custom_resources"]
```

### Step 4: Enable in Main

Your custom resources are automatically loaded if the `custom/__init__.py` exports them. The `__main__.py` orchestrates everything.

---

## 💡 Best Practices

### Code Organization

**Do:**
- ✅ Create separate files for different features
- ✅ Use meaningful module names
- ✅ Return created resources for reference
- ✅ Apply tags to all resources

**Don't:**
- ❌ Modify files in `core/` directory
- ❌ Duplicate core functionality
- ❌ Hardcode values (use config)
- ❌ Create circular dependencies

### Resource Naming

Use consistent naming conventions:

```python
# Good - descriptive, prefixed
custom_lambda = aws.lambda_.Function(
    "salesforce-integration",
    name=f"{project}-{stack}-salesforce-sync",
    ...
)

# Bad - generic, unclear
lambda1 = aws.lambda_.Function(
    "fn",
    name="function",
    ...
)
```

### Configuration Management

Store custom settings in your Pulumi config:

```yaml
# Pulumi.dev.yaml
config:
  # Core settings
  connect:instanceAlias: my-instance
  
  # Your custom settings
  custom:
    salesforce:
      instanceUrl: https://your-org.salesforce.com
      apiVersion: "58.0"
    zendesk:
      subdomain: your-company
      apiToken: encrypted-token
```

Access in your code:

```python
import pulumi

config = pulumi.Config("custom")
salesforce_url = config.require("salesforce:instanceUrl")
zendesk_subdomain = config.require("zendesk:subdomain")
```

### Error Handling

Always handle potential errors:

```python
def create_custom_resources(core_resources, tags):
    # Validate required resources exist
    if "connect_instance" not in core_resources:
        raise ValueError("Connect instance not found in core resources")
    
    try:
        # Create resources
        lambda_function = aws.lambda_.Function(...)
        
    except Exception as e:
        pulumi.log.error(f"Failed to create custom resources: {e}")
        raise
    
    return {"lambda": lambda_function}
```

---

## 📖 Additional Resources

- [Pulumi Python Documentation](https://www.pulumi.com/docs/languages-sdks/python/)
- [AWS Provider Documentation](https://www.pulumi.com/registry/packages/aws/)

---

## 🆘 Support

For help with custom extensions:
- 🐛 [Open an Issue](https://github.com/bloy.me.uk/elevai-connect/issues)
- 💬 [Start a Discussion](https://github.com/bloy.me.uk/elevai-connect/discussions)
