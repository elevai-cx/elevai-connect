# Using Claude Code with elevai-connect

Manage your Amazon Connect infrastructure through Claude Code's command-line interface.

## What You Can Do

- Deploy infrastructure: "Deploy the latest changes to dev"
- Preview changes: "Show me what would change if I deployed to staging"
- Manage configuration: "Update the alarm threshold to 75% in prod"
- Switch environments: "Switch to the production stack"
- Query resources: "What's the Connect instance ID for dev?"

## Quick Start

### Prerequisites

- Claude Code installed (`npm install -g @anthropic-ai/claude-code`)
- This project cloned and set up (see [Getting Started](GETTING_STARTED.md))

### Start Using

```bash
cd /path/to/elevai-connect
claude
```

Try: "List all available Pulumi stacks"

## Example Workflows

### Deploy Changes

```
> Deploy my latest changes to dev

Claude: Let me preview the changes first.
[Shows preview of 3 alarm updates]
Would you like me to proceed?

> Yes

Claude: Running pulumi up. You'll need to approve in terminal.
[Waits for your terminal approval]
Deployment complete!
```

**Important**: Manual approval is always required in your terminal for deployments.

### Check Configuration

```
> What's the monthly budget for production?

Claude: The current budget limit for production is $500.
```

## Safety Features

**Manual Approval Required**: Claude never uses `--yes` flag. You must review and approve all changes in your terminal.

**Auto-approved (read-only)**: Preview changes, list stacks, read configuration, view outputs.

**Requires terminal confirmation**: Deploy (`pulumi up`), destroy resources (`pulumi destroy`).

## Troubleshooting

### Pulumi not in PATH
```bash
export PATH="$PATH:$HOME/.pulumi/bin"
```

### AWS credentials
```bash
aws configure
aws sts get-caller-identity  # Verify
```

## Security Best Practices

1. Manual approval enforced - never auto-deploys
2. Use separate AWS accounts for dev/staging/prod
3. Review previews carefully before deploying
4. Test in dev first
5. Use IAM roles with appropriate permissions

## Getting Help

- **Claude Code Docs**: https://docs.claude.com/en/docs/claude-code
- **Pulumi Docs**: https://www.pulumi.com/docs/
