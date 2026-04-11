# Custom Extensions - Claude Guide

## File Modification Rules

| Directory/File          | Can Modify? | Purpose                                            |
| ----------------------- | ----------- | -------------------------------------------------- |
| `custom/`               | YES         | Add custom extensions here                         |
| `Pulumi.<stack>.yaml`   | YES         | Stack configuration                                |
| `core/`                 | NO          | Core infrastructure (maintained by project owners) |
| `__main__.py`           | NO          | Main entry point                                   |
| `Pulumi.yaml`           | NO          | Project definition                                 |

**If a change requires modifying core:**
1. Suggest creating an extension in `custom/` directory instead
2. Show how to use `core_resources` dict to access what's needed
3. Only modify core if the user explicitly insists

## Deployment Safety

| Action              | Correct Method                  | Never Do This                                |
| ------------------- | ------------------------------- | -------------------------------------------- |
| **Preview changes** | `pulumi preview` (bash)         | -                                            |
| **Deploy**          | MCP tool: `pulumi_up`           | `pulumi up` (bash) / `pulumi up --yes`       |
| **Destroy**         | MCP tool: `pulumi_destroy`      | `pulumi destroy` (bash)                      |
| **Change config**   | MCP tool: `update_stack_config` | `pulumi config set` (bash)                   |
| **Read config**     | MCP tool: `read_stack_config`   | `pulumi config get` (bash - OK)              |

**Deployment Workflow:**
1. Run `pulumi preview --stack <stack>` (bash command)
2. Show preview to user
3. Ask for confirmation
4. Use MCP tool `pulumi_up` with stack parameter
5. Wait for completion

## Adding Custom Resources

All custom code goes in the `custom/` directory. This keeps your extensions separate from core infrastructure so you can pull upstream updates without conflicts.

```python
# custom/my_integration.py
import pulumi_aws as aws

def create_my_integration(core_resources, tags):
    """Create custom resources."""
    connect_id = core_resources.get("connect_instance_id")
    s3_buckets = core_resources.get("s3_buckets", {})
    
    my_lambda = aws.lambda_.Function(
        "my-lambda",
        runtime="python3.13",
        handler="index.handler",
        role=my_role.arn,
        code=pulumi.AssetArchive({
            ".": pulumi.FileArchive("./lambda-code/my-function")
        }),
        tags=tags
    )
    
    return {"my_lambda": my_lambda}
```

Register it in `custom/__init__.py`:

```python
from .my_integration import create_my_integration

def initialize_custom_resources(core_resources, tags):
    custom = {}
    integration = create_my_integration(core_resources, tags)
    custom.update(integration)
    return custom
```

### Core Resources Available

```python
{
    "connect_instance_id": pulumi.Output[str],
    "connect_instance_arn": pulumi.Output[str],
    "s3_buckets": {...},
    "lambda_functions": {...},
    "iam": {...},
    "qconnect": {...},
    "kms_keys": {...},
    "alarms": {...}
}
```

## Documentation

- **Getting Started**: `docs/GETTING_STARTED.md`
- **Custom Extensions Guide**: `docs/CUSTOM_EXTENSIONS_GUIDE.md`
- **Parameter Store Guide**: `docs/PARAMETER_STORE_GUIDE.md`
