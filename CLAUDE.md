# Amazon Connect Pulumi Infrastructure Project

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

**Why:** Bash preview shows changes clearly. MCP tools use `--skip-preview` flag and work in non-interactive mode. NEVER use `--yes` flag.

## Project Structure

```
/
├── __main__.py              # Main entry point
├── Pulumi.yaml             # Project definition (committed)
├── Pulumi.<stack>.yaml     # Stack config (NOT committed)
├── requirements.txt        # Python dependencies
├── core/                   # Core infrastructure
│   ├── connect.py
│   ├── s3.py
│   ├── iam.py
│   ├── lambda_functions.py
│   ├── qconnect.py
│   └── alerting/
├── custom/                # Custom extensions
│   └── __init__.py
├── lambda-code/           # Lambda source code
├── examples/              # Sample files (Q knowledgebase etc.)
└── docs/                  # Documentation
```

## Configuration

### Critical: Cannot Change After Deployment
- `connect:instanceAlias` - Must be globally unique
- `connect:identityManagementType` - SAML or CONNECT_MANAGED

### Required Configuration

```yaml
aws:region: eu-west-2
alerting:error_email: "ops@example.com"
billing:notificationEmail: "billing@example.com"
connect:instanceAlias: your-unique-alias
connect:identityManagementType: SAML  # or CONNECT_MANAGED
```

### Modifying Configuration

```
User: "Enable QConnect"

Claude:
1. Use MCP tool: update_stack_config
   stack="dev"
   updates={"qconnect:enabled": true}

2. Run bash: pulumi preview --stack dev
   (Show preview to user)

3. Ask: "Would you like to deploy?"

4. Use MCP tool: pulumi_up with stack="dev"
```

## Adding Custom Resources

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

## Essential Commands

### Safe for Bash
```bash
pulumi preview                  # Review changes (ALWAYS run first)
pulumi stack output            # View outputs
pulumi stack ls                # List stacks
pulumi config get <key>        # Read config value
pulumi refresh                 # Sync state with AWS
```

### Use MCP Tools (NOT Bash)
- `pulumi up` → Use MCP: `pulumi_up`
- `pulumi destroy` → Use MCP: `pulumi_destroy`
- `pulumi config set` → Use MCP: `update_stack_config`

## Troubleshooting

| Issue                     | Solution                                        |
| ------------------------- | ----------------------------------------------- |
| "Resource already exists" | Use `pulumi import` to import existing resource |
| "No updates to perform"   | Run `pulumi refresh` to sync state              |
| "Concurrent modification" | Wait for other operation or `pulumi cancel`     |
| Authentication errors     | Verify: `aws sts get-caller-identity`           |

## Documentation

- **Getting Started**: `docs/GETTING_STARTED.md`
- **Post-Deployment Steps**: `docs/POST_DEPLOYMENT_STEPS.md`
- **SAML Setup**: `docs/SAML_SETUP_GUIDE.md`
- **Amazon Q**: `docs/AMAZON_Q_GUIDE.md`
- **Monitoring**: `docs/MONITORING_GUIDE.md`
- **Custom Extensions**: `docs/CUSTOM_EXTENSIONS_GUIDE.md`
- **Analytics Data Lake**: `docs/ANALYTICS_DATA_LAKE.md`
- **Parameter Store**: `docs/PARAMETER_STORE_GUIDE.md`
