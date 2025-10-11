# Amazon Connect Pulumi Infrastructure Project

## ⚠️ CRITICAL SAFETY RULES

**Claude MUST follow these rules when working with this project:**

### Deployment Safety

| Action              | Correct Method                  | ❌ Never Do This                             |
| ------------------- | ------------------------------- | ------------------------------------------- |
| **Preview changes** | `pulumi preview` (bash)         | -                                           |
| **Deploy**          | MCP tool: `pulumi_up`           | ❌ `pulumi up` (bash)<br>❌ `pulumi up --yes` |
| **Destroy**         | MCP tool: `pulumi_destroy`      | ❌ `pulumi destroy` (bash)                   |
| **Change config**   | MCP tool: `update_stack_config` | ❌ `pulumi config set` (bash)                |
| **Read config**     | MCP tool: `read_stack_config`   | `pulumi config get` (bash - OK)             |

**Deployment Workflow:**
1. Run `pulumi preview --stack <stack>` (bash command)
2. Show preview to user
3. Ask for confirmation
4. Use MCP tool `pulumi_up` with stack parameter
5. Wait for completion

**Why:** Bash preview shows changes clearly. MCP tools use `--skip-preview` flag and work in non-interactive mode. NEVER use `--yes` flag.

### File Modification Rules

| Directory/File          | Can Modify? | Purpose                                            |
| ----------------------- | ----------- | -------------------------------------------------- |
| ✅ `custom/`             | YES         | Add custom extensions here                         |
| ✅ `Pulumi.<stack>.yaml` | YES         | Stack configuration                                |
| ❌ `core/`               | NO          | Core infrastructure (maintained by project owners) |
| ❌ `__main__.py`         | NO          | Main entry point                                   |
| ❌ `Pulumi.yaml`         | NO          | Project definition                                 |
| ❌ `mcp-server/`         | NO          | MCP server code                                    |

**If user requests core changes:**
1. Explain core files shouldn't be modified
2. Suggest creating extension in `custom/` directory
3. Show how to use `core_resources` dict
4. Only modify core if user explicitly insists

---

## Project Overview

Production-ready Pulumi project for Amazon Connect contact centers with monitoring, security, and AI capabilities.

**Key Features:**
- Amazon Connect with SAML or managed authentication
- 70+ CloudWatch alarms
- Amazon Q in Connect
- Modular architecture (core + custom)

## Project Structure

```
/
├── __main__.py              # Main entry point
├── Pulumi.yaml             # Project definition (committed)
├── Pulumi.<stack>.yaml     # Stack config (NOT committed)
├── requirements.txt        # Python dependencies
├── core/                   # Core infrastructure (DON'T MODIFY)
│   ├── connect.py
│   ├── s3.py
│   ├── iam.py
│   ├── lambda_functions.py
│   ├── qconnect.py
│   └── alerting/
├── custom/                # Custom extensions (MODIFY HERE)
│   └── __init__.py
├── lambda-code/           # Lambda source code
├── workshops/             # Hands-on tutorials
└── docs/                  # Documentation
```

## Configuration Management

### Configuration Files

| File                          | Purpose            | Committed? |
| ----------------------------- | ------------------ | ---------- |
| `Pulumi.yaml`                 | Project definition | ✅ Yes      |
| `Pulumi.<stack>.yaml`         | Stack config       | ❌ No       |
| `Pulumi.<stack>.yaml.example` | Template           | ✅ Yes      |

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

### Modifying Configuration - Correct Workflow

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

## Common Workflows

### Initial Setup

```bash
# 1. Setup environment
git clone <repo>
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure Pulumi
pulumi login
cp Pulumi.dev.yaml.example Pulumi.dev.yaml
# Edit Pulumi.dev.yaml with your values

# 3. Initialize and deploy
pulumi stack init dev
pulumi preview  # Review changes
pulumi up       # Deploy (manual approval required)
```

### Adding Custom Resources

**Always add to `custom/` directory - never modify `core/`**

```python
# custom/my_integration.py
import pulumi_aws as aws

def create_my_integration(core_resources, tags):
    """Create custom resources."""
    
    # Access core resources (read-only)
    connect_id = core_resources.get("connect_instance_id")
    s3_buckets = core_resources.get("s3_buckets", {})
    
    # Create your resources
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

```python
# custom/__init__.py
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
- ❌ `pulumi up` → Use MCP: `pulumi_up`
- ❌ `pulumi destroy` → Use MCP: `pulumi_destroy`
- ❌ `pulumi config set` → Use MCP: `update_stack_config`

## Workshops & Tutorials

Hands-on workshops for implementing features. Located in `/workshops/` directory.

### Available Workshops

#### 1. Amazon Q Knowledge Base Setup
**Path:** `workshops/q-knowledgebase-set-up/`  
**Duration:** 30 minutes  
**Level:** Beginner

**Topics:**
- Upload documents to Q Knowledge Base
- Configure metadata and tagging
- Create Lex bots for FAQ handling
- Import Connect contact flows
- Test Q integration in chat

**Prerequisites:**
- Amazon Connect instance deployed
- AWS Console access
- Pulumi CLI configured

**Start:** [workshops/q-knowledgebase-set-up/README.md](workshops/q-knowledgebase-set-up/README.md)

### Using Workshops

1. Check prerequisites
2. Read entire workshop first
3. Follow steps sequentially, do not do more that 1 step at a time
4. Use Claude Code for questions
5. Verify outputs and troubleshoot

### Workshop Structure

Each workshop contains:
- Comprehensive README.md
- Sample files and resources
- Troubleshooting guidance
- Links to additional resources

## Deployment Best Practices

### Pre-Deployment Checklist
1. ✅ Review config changes: `git diff`
2. ✅ Preview: `pulumi preview`
3. ✅ Check for breaking changes
4. ✅ Verify email addresses
5. ✅ Confirm budget limits

### Deployment Process
```bash
# 1. Preview and save
pulumi preview > preview.txt

# 2. Review preview.txt thoroughly

# 3. Deploy (manual approval required)
pulumi up

# 4. Verify
pulumi stack output
```

### Rollback Strategy
```bash
# Backup before deployment
pulumi stack export --file backup-$(date +%Y%m%d).json

# Cancel if issues arise
Ctrl+C

# Restore previous state if needed
pulumi stack import --file backup-previous.json
pulumi refresh
```

## Troubleshooting

| Issue                     | Solution                                        |
| ------------------------- | ----------------------------------------------- |
| "Resource already exists" | Use `pulumi import` to import existing resource |
| "No updates to perform"   | Run `pulumi refresh` to sync state              |
| "Concurrent modification" | Wait for other operation or `pulumi cancel`     |
| Authentication errors     | Verify: `aws sts get-caller-identity`           |

## Security

### Secrets Management
- Use `pulumi config set --secret` for sensitive values
- Never commit `Pulumi.<stack>.yaml` with secrets
- Secrets encrypted in Pulumi state
- Use AWS Secrets Manager for runtime secrets

### Encryption
All data encrypted at rest:
- S3: SSE-KMS with customer keys
- DynamoDB: At-rest encryption
- CloudWatch Logs: Encrypted
- Kinesis Streams: Encrypted

## Integration Points

### Parameter Store Exports

Core resources exported to SSM Parameter Store:

```
/elevai-connect/{stack}/connect/instance-id
/elevai-connect/{stack}/connect/instance-arn
/elevai-connect/{stack}/s3/recordings-bucket
/elevai-connect/{stack}/qconnect/assistant-id
```

External apps can read these without Pulumi dependency.

## Monitoring

### Alarm Categories
- **ERROR**: Critical - immediate action required
- **WARNING**: Important trends to monitor
- **INFO**: Informational notifications

### CloudWatch Logs
```bash
# List log groups
aws logs describe-log-groups --log-group-name-prefix /aws/connect

# Tail Lambda logs
aws logs tail /aws/lambda/<function-name> --follow
```

## Advanced Usage

### Multiple Environments
```bash
pulumi stack select dev && pulumi up
pulumi stack select staging && pulumi up
pulumi stack select prod && pulumi up
```

### CI/CD Integration
```bash
export PULUMI_ACCESS_TOKEN=<token>
export AWS_ACCESS_KEY_ID=<key>
export AWS_SECRET_ACCESS_KEY=<secret>

pulumi up --yes --stack prod  # OK in CI/CD only
```

## Key Configuration Reference

```yaml
# Required
aws:region: eu-west-2
connect:instanceAlias: "unique-alias"          # PERMANENT
connect:identityManagementType: "SAML"         # PERMANENT

# SAML (if applicable)
connect:samlMetadataFile: "path/to/metadata.xml"

# Alerting
alerting:error_email: "ops@example.com"

# Budget
billing:notificationEmail: "billing@example.com"
billing:monthlyBudgetLimit: 1000

# Amazon Q
qconnect:enabled: true

# S3 Lifecycle
s3:recordings.deletionDays: 90
```

## Documentation

- **SAML Setup**: `docs/SAML_SETUP_GUIDE.md`
- **Amazon Q**: `docs/AMAZON_Q_GUIDE.md`
- **Monitoring**: `docs/MONITORING_GUIDE.md`
- **Custom Extensions**: `docs/CUSTOM_EXTENSIONS_GUIDE.md`
- **Claude Code Setup**: `docs/CLAUDE_CODE_SETUP.md`

## Remember

✅ **DO:**
- Use bash for `pulumi preview`
- Use MCP tools for `pulumi up`, `destroy`, and config changes
- Always show preview before deploying
- Only modify files in `custom/` directory
- Test in dev before production

❌ **DON'T:**
- Never use `--yes` flag
- Never run `pulumi destroy` as bash command
- Never modify `core/` directory
- Never commit stack config files with secrets
- Never skip preview before deployment

---

*Note: `instanceAlias` and `identityManagementType` are permanent - cannot be changed after deployment.*
