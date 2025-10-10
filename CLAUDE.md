# Amazon Connect Pulumi Infrastructure Project

## ⚠️ CRITICAL SAFETY RULES FOR CLAUDE

**When working with this project, Claude MUST follow these rules:**

### 🚨 Deployment Safety

1. ✅ **Use bash command** for `pulumi preview` (read-only, shows changes)
2. ✅ **Use MCP tool** `pulumi_up` for deployment (uses --skip-preview flag)
3. ❌ **NEVER** run `pulumi destroy` as a bash command - use MCP tool `pulumi_destroy` only
4. ❌ **NEVER** use `--yes` flag with any Pulumi commands
5. ✅ ALWAYS show preview before deploying

**Why this workflow:** Bash `pulumi preview` shows changes clearly. MCP `pulumi_up` uses `--skip-preview` flag (safer than `--yes`) and works in non-interactive mode. The preview MUST be shown first.

### ⚙️ Configuration Management

1. ✅ **ALWAYS use MCP tool** `update_stack_config` to modify configuration
2. ❌ **NEVER** run `pulumi config set` bash commands
3. ✅ After updating config, run `pulumi preview` bash command to see changes
4. ✅ Then use MCP tool `pulumi_up` to deploy
5. ✅ Use `read_stack_config` MCP tool to read current configuration

**Why:** Configuration should be maintained in `Pulumi.*.yaml` files which can be version controlled and reviewed. The MCP tool `update_stack_config` modifies these YAML files directly.

### 📁 File Modification Rules

**Files Claude CAN modify:**
- ✅ `custom/` directory - Add new Python modules here
- ✅ `Pulumi.dev.yaml` - Stack-specific configuration
- ✅ `Pulumi.staging.yaml` - Stack-specific configuration  
- ✅ `Pulumi.prod.yaml` - Stack-specific configuration

**Files Claude MUST NEVER modify:**
- ❌ `core/` directory - Core infrastructure (maintained by project owners)
- ❌ `__main__.py` - Main entry point
- ❌ `Pulumi.yaml` - Project definition
- ❌ `mcp-server/` - MCP server code
- ❌ Any Python files outside `custom/`

**Why:** The `core/` directory contains the project's infrastructure foundation. Users should only extend via `custom/` directory to keep their changes separate from core updates.

**If a user asks to modify core infrastructure:**
1. Explain that core files shouldn't be modified directly
2. Suggest creating a custom extension in `custom/` directory instead
3. Show how to use `core_resources` dict to reference core infrastructure
4. Only modify core files if user explicitly insists and understands the risks

**Correct approach for deployments:**
- Run `pulumi preview --stack <stack>` (bash command, read-only)
- Use MCP tool `pulumi_up` with stack parameter (uses --skip-preview)
- ALWAYS show preview before deployment

**Correct approach for destroy:**
- Use MCP tool: `pulumi_destroy` (NOT bash command)
- Extra safeguards in MCP tool

**NEVER do this:**
- ❌ `pulumi destroy` (bash command - use MCP tool instead)
- ❌ `pulumi up --yes` (bash command with --yes flag)
- ❌ `pulumi destroy --yes` (bash command with --yes flag)

---

## Project Overview

Production-ready Pulumi project for deploying Amazon Connect contact centers with comprehensive monitoring, security, and AI capabilities. Written in Python with a modular architecture separating core infrastructure from custom extensions.

**Key Features:**
- Amazon Connect with SAML or managed authentication
- 70+ CloudWatch alarms for monitoring
- Amazon Q in Connect for AI assistance
- Modular architecture (core + custom)

## Project Structure

```
/
├── __main__.py              # Main entry point
├── Pulumi.yaml             # Project definition (committed)
├── Pulumi.<stack>.yaml     # Stack config (NOT committed - personal)
├── mcp.json                # MCP server configuration
├── Claude.md               # This file
├── requirements.txt        # Python dependencies
├── core/                   # Core infrastructure modules
│   ├── connect.py         # Amazon Connect resources
│   ├── s3.py              # S3 buckets
│   ├── iam.py             # IAM roles and SAML
│   ├── lambda_functions.py # Lambda deployments
│   ├── qconnect.py        # Amazon Q integration
│   └── alerting/          # CloudWatch alarms
├── custom/                # Custom extensions (user-defined)
│   └── __init__.py
├── mcp-server/            # MCP server for Claude Code
├── lambda-code/           # Lambda function source code
├── docs/                  # Documentation
└── scripts/               # Utility scripts
```

## Key Commands

### 🚨 IMPORTANT: When to Use MCP Tools vs Bash Commands

**Use MCP Tools (NOT bash commands) for:**
- ❌ `pulumi up` → Use MCP tool: `pulumi_up` (uses --skip-preview)
- ❌ `pulumi destroy` → Use MCP tool: `pulumi_destroy` (NEVER bash)
- ❌ `pulumi config set` → Use MCP tool: `update_stack_config`
- ✅ Modifying configuration → Use MCP tool: `update_stack_config`

**Safe to use bash commands for:**
- ✅ `pulumi preview` (read-only, shows changes - ALWAYS run before deployment)
- ✅ `pulumi stack output`
- ✅ `pulumi stack ls`
- ✅ `pulumi config get`
- ✅ `pulumi refresh`

**CRITICAL:** ALWAYS run `pulumi preview` before using `pulumi_up` MCP tool. Never use `--yes` flag.

### Essential Pulumi Commands (For Direct Terminal Use)

**Note:** Claude should use bash for `pulumi preview` (read-only) and MCP tool `pulumi_up` for deployments. Use MCP tools for `pulumi destroy` and configuration changes.

```bash
# Preview changes before applying
pulumi preview

# Deploy infrastructure
pulumi up

# Destroy all resources (ALWAYS requires manual approval)
pulumi destroy

# Refresh state from actual AWS resources
pulumi refresh

# View stack outputs
pulumi stack output

# View all stack outputs as JSON
pulumi stack output --json

# List all stacks
pulumi stack ls

# Select a different stack
pulumi stack select <stack-name>

# Configuration commands (Claude should use update_stack_config MCP tool instead)
pulumi config set <key> <value>
pulumi config set --secret <key> <value>
pulumi config get <key>
```

## Configuration Management

### Configuration Files

| File                          | Purpose               | Committed? |
| ----------------------------- | --------------------- | ---------- |
| `Pulumi.yaml`                 | Project definition    | ✅ Yes      |
| `Pulumi.<stack>.yaml`         | Stack-specific config | ❌ No       |
| `Pulumi.<stack>.yaml.example` | Template              | ✅ Yes      |

### Critical Configuration Values

⚠️ **These CANNOT be changed after initial deployment:**
- `connect:instanceAlias` - Must be globally unique
- `connect:identityManagementType` - Either SAML or CONNECT_MANAGED

### Required Configuration

```yaml
# Minimum required configuration
aws:region: eu-west-2
alerting:error_email: "ops@example.com"
billing:notificationEmail: "billing@example.com"
connect:instanceAlias: your-unique-alias
connect:identityManagementType: SAML  # or CONNECT_MANAGED
```

## Common Workflows

### 🚨 Deploying Infrastructure (CRITICAL - Read This First!)

**When a user asks to deploy, Claude MUST:**

1. **First**: Run `pulumi preview --stack <stack>` as a bash command
2. **Show the preview** to the user in detail
3. **Ask for confirmation**: "Would you like me to proceed with deployment?"
4. **If yes**: Use MCP tool `pulumi_up` with stack parameter
5. **Explain**: "I'll deploy using the MCP tool with --skip-preview flag."
6. **Wait** for the deployment to complete

**Example correct workflow:**
```
User: "Deploy my changes to dev"

Claude: "Let me preview the changes first."
[Runs bash command: pulumi preview --stack dev]
[Shows preview output]

"The preview shows:
- 2 resources will be updated
- 0 resources will be created
- 0 resources will be deleted

Would you like me to proceed with deployment?"

User: "Yes"

Claude: "I'll deploy now using the MCP tool with --skip-preview flag."
[Calls MCP tool: pulumi_up with stack="dev"]

"Deployment complete! ✓"
```

**WRONG - NEVER DO THIS:**
```
User: "Deploy my changes to dev"
Claude: [Runs: pulumi up --stack dev]  ❌ WRONG! Use MCP tool!
Claude: [Runs: pulumi up --stack dev --yes]  ❌ WRONG! Never use --yes!

User: "Destroy the dev stack"
Claude: [Runs: pulumi destroy --stack dev]  ❌ WRONG! Use MCP tool!
```

### Initial Setup

1. Clone the repository
2. Create and activate virtual environment
3. Install dependencies: `pip install -r requirements.txt`
4. Login to Pulumi: `pulumi login`
5. Create stack config: `cp Pulumi.dev.yaml.example Pulumi.dev.yaml`
6. Edit configuration with your values
7. Initialize stack: `pulumi stack init dev`
8. Preview: `pulumi preview`
9. Deploy: `pulumi up`

### Adding Custom Resources

**⚠️ IMPORTANT: Always add custom code to `custom/` directory, NEVER modify `core/` files.**

1. Create Python module in `custom/` directory (e.g., `custom/my_integration.py`)
2. Import and initialize in `custom/__init__.py`
3. Use `core_resources` dict to reference core infrastructure
4. Deploy: `pulumi preview` (bash) then use MCP tool `pulumi_up`

**Example: Adding a custom Lambda function**

```python
# custom/my_integration.py
import pulumi
import pulumi_aws as aws

def create_my_integration(core_resources, tags):
    """Create custom integration resources."""
    
    # Access core resources (don't modify them!)
    connect_id = core_resources.get("connect_instance_id")
    s3_buckets = core_resources.get("s3_buckets", {})
    recordings_bucket = s3_buckets.get("recordings")
    
    # Create your custom Lambda
    my_lambda = aws.lambda_.Function(
        "my-custom-lambda",
        runtime="python3.13",
        handler="index.handler",
        role=my_role.arn,
        code=pulumi.AssetArchive({
            ".": pulumi.FileArchive("./lambda-code/my-function")
        }),
        tags=tags
    )
    
    return {
        "my_lambda": my_lambda
    }
```

```python
# custom/__init__.py
from .my_integration import create_my_integration

def initialize_custom_resources(core_resources, tags):
    """Initialize all custom resources."""
    custom = {}
    
    # Add your integration
    integration = create_my_integration(core_resources, tags)
    custom.update(integration)
    
    return custom
```

**Why we use `custom/` directory:**
- Keeps your changes separate from core infrastructure
- Makes it easy to update core infrastructure without conflicts
- Clear separation between maintained core and user extensions
- Your custom code is portable across core updates

### Modifying Configuration

**⚠️ IMPORTANT: Use MCP tools to modify configuration, NOT bash commands.**

**Correct workflow:**

1. Use `update_stack_config` MCP tool to modify the YAML file
2. Run `pulumi preview` bash command to see the changes
3. Use MCP tool `pulumi_up` to deploy

**Example correct workflow:**
```
User: "Change the QConnect setting to enabled"

Claude:
[Calls MCP tool: update_stack_config with:
  stack="dev"
  updates={"qconnect:enabled": true}
]

"I've updated qconnect:enabled to true in Pulumi.dev.yaml.

Would you like me to preview the infrastructure changes?"

User: "Yes"

Claude:
[Runs bash: pulumi preview --stack dev]

"The preview shows 3 resources will be updated. Would you like to deploy?"

User: "Yes"

Claude:
[Calls MCP tool: pulumi_up with stack="dev"]

"Deploying with --skip-preview flag..."
"Deployment complete! ✓"
```

**WRONG - NEVER DO THIS:**
```
User: "Change QConnect to enabled"
Claude: [Runs bash: pulumi config set qconnect:enabled true]  ❌ WRONG!
```

## Important Constraints

### Amazon Connect Limitations

1. **Instance Alias**: Cannot be changed after creation
2. **Identity Management Type**: Cannot be changed after creation
3. **SAML Metadata**: Can be updated after deployment
4. **Service Quotas**: Check and request increases before production

### Pulumi State

- Stack state stored in Pulumi backend (cloud or local)
- NEVER manually edit state files
- Use `pulumi refresh` if state is out of sync
- Back up state regularly: `pulumi stack export`

## Working with Core Modules

### Core Module Return Values

The `create_core_infrastructure()` function returns a dict with:

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

### Accessing Core Resources in Custom Code

```python
def initialize_custom_resources(core_resources, tags):
    # Get Connect instance ID
    connect_id = core_resources.get("connect_instance_id")
    
    # Get S3 buckets
    s3_buckets = core_resources.get("s3_buckets", {})
    recordings_bucket = s3_buckets.get("recordings")
    
    # Get Lambda functions
    lambdas = core_resources.get("lambda_functions", {})
    
    # Get Q Connect resources
    qconnect = core_resources.get("qconnect", {})
    assistant_id = qconnect.get("assistant_id")
    
    return {}
```

## Deployment Best Practices

### Pre-Deployment Checklist

1. Review configuration changes: `git diff`
2. Preview changes: `pulumi preview`
3. Check for breaking changes in output
4. Verify email addresses for alerts
5. Confirm budget limits are appropriate

### Deployment Process

```bash
# 1. Preview
pulumi preview > preview.txt
# Review preview.txt

# 2. Deploy (requires manual approval at prompt)
pulumi up

# 3. Verify outputs
pulumi stack output

# 4. Test critical paths
```

⚠️ **IMPORTANT SAFETY FEATURE**: When using Claude Code with the MCP server, `pulumi up` and `pulumi destroy` commands NEVER use the `--yes` flag. You will always be prompted to manually review and approve changes in your terminal. This prevents accidental deployments or resource destruction.

### Rollback Strategy

```bash
# Export current state as backup
pulumi stack export --file backup-$(date +%Y%m%d).json

# If deployment fails, cancel
Ctrl+C

# To rollback, restore previous state
pulumi stack import --file backup-previous.json
pulumi refresh
```

## Troubleshooting

### Common Issues

**"Resource already exists" Error**
- Check if resource was created outside Pulumi
- Use `pulumi import` to import existing resource

**"No updates to perform"**
- Configuration may not have changed
- State may be out of sync: run `pulumi refresh`

**"Concurrent modification" Error**
- Another user is running pulumi simultaneously
- Wait for other operation to complete
- Check for stale locks: `pulumi cancel`

**Authentication Errors**
- Verify AWS credentials: `aws sts get-caller-identity`
- Check region configuration matches AWS CLI

## Security Considerations

### Secrets Management

- Use `pulumi config set --secret` for sensitive values
- Never commit `Pulumi.<stack>.yaml` files with secrets
- Secrets are encrypted in Pulumi state
- Use AWS Secrets Manager for runtime secrets

### Encryption

All data is encrypted:
- S3: SSE-KMS with customer-managed keys
- DynamoDB: At-rest encryption
- CloudWatch Logs: Encrypted
- Kinesis Streams: Encrypted

## Integration Points

### Parameter Store

Core resources are exported to AWS Systems Manager Parameter Store:

```
/elevai-connect/{stack}/connect/instance-id
/elevai-connect/{stack}/connect/instance-arn
/elevai-connect/{stack}/s3/recordings-bucket
/elevai-connect/{stack}/qconnect/assistant-id
```

External applications can read these values without direct Pulumi dependency.

## Monitoring

### Alarm Categories

- **ERROR**: Critical issues requiring immediate action
- **WARNING**: Important trends to monitor
- **INFO**: Informational notifications

### Accessing Logs

```bash
# View CloudWatch log groups
aws logs describe-log-groups --log-group-name-prefix /aws/connect

# Tail logs for Lambda function
aws logs tail /aws/lambda/<function-name> --follow
```

## Advanced Usage

### Multiple Environments

```bash
# Development
pulumi stack select dev
pulumi up

# Staging
pulumi stack select staging
pulumi up

# Production
pulumi stack select prod
pulumi up --yes  # If in CI/CD
```

### CI/CD Integration

```bash
# Set Pulumi token
export PULUMI_ACCESS_TOKEN=<token>

# Set AWS credentials
export AWS_ACCESS_KEY_ID=<key>
export AWS_SECRET_ACCESS_KEY=<secret>

# Deploy
pulumi up --yes --stack prod
```

## Support Resources

- **Documentation**: `/docs` directory
- **SAML Setup**: `docs/SAML_SETUP_GUIDE.md`
- **Amazon Q**: `docs/AMAZON_Q_GUIDE.md`
- **Monitoring**: `docs/MONITORING_GUIDE.md`
- **Custom Extensions**: `docs/CUSTOM_EXTENSIONS_GUIDE.md`
- **Claude Code Setup**: `docs/CLAUDE_CODE_SETUP.md`

## Quick Reference

### Common Configuration Keys

```yaml
aws:region                          # AWS region
connect:instanceAlias              # Connect instance alias (PERMANENT)
connect:identityManagementType     # SAML or CONNECT_MANAGED (PERMANENT)
connect:samlMetadataFile          # Path to SAML metadata XML
alerting:error_email              # Email for critical alerts
billing:monthlyBudgetLimit        # Monthly budget in USD
qconnect:enabled                  # Enable Amazon Q
s3:recordings.deletionDays        # Days before deleting recordings
```

## Remember

### 🔒 CRITICAL SAFETY RULES (Read Every Time)

**Deployment:**
1. ✅ **Use bash** for `pulumi preview` (read-only, shows changes)
2. ✅ **Use MCP tool** `pulumi_up` for deployment (uses --skip-preview)
3. ❌ **NEVER** use `--yes` flag with any Pulumi command
4. ❌ **NEVER** run `pulumi destroy` as bash - use MCP tool `pulumi_destroy` only
5. ✅ **ALWAYS** show preview before deploying

**Configuration:**
1. ❌ **NEVER** run `pulumi config set` bash commands
2. ✅ **ALWAYS** use MCP tool `update_stack_config` to modify configuration
3. ✅ After config changes, use `pulumi preview` then MCP tool `pulumi_up`
4. ✅ Use `read_stack_config` to read current configuration

**File Modifications:**
1. ✅ **ONLY** modify files in `custom/` directory for extensions
2. ✅ **ONLY** modify `Pulumi.<stack>.yaml` for configuration
3. ❌ **NEVER** modify `core/` directory files
4. ❌ **NEVER** modify `__main__.py` or `Pulumi.yaml`
5. ✅ If user needs core changes, create `custom/` extension instead

### Other Important Things

- ⚠️ `instanceAlias` and `identityManagementType` are PERMANENT
- 📧 Always configure alert emails before deployment
- 🔒 Never commit stack configuration files with secrets
- 🧪 Test in dev environment before deploying to production
- 💾 Back up stack state before major changes
- 📊 Monitor alarms after deployment
- 📝 Document all custom extensions
