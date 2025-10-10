# Using Claude Code with Amazon Connect Pulumi

Manage your Amazon Connect infrastructure through Claude Code's command-line interface using the included MCP server.

## What You Can Do

- 🚀 Deploy infrastructure: "Deploy the latest changes to dev"
- 👀 Preview changes: "Show me what would change if I deployed to staging"
- ⚙️ Manage configuration: "Update the alarm threshold to 75% in prod"
- 🔄 Switch environments: "Switch to the production stack"
- 📊 Query resources: "What's the Connect instance ID for dev?"

## Quick Start

### Prerequisites

- Claude Code installed (`npm install -g @anthropic-ai/claude-code`)
- Node.js 18+ installed
- This project cloned

### 1. Build the MCP Server

```bash
cd /path/to/elevai-connect/mcp-server
npm install
npm run build
```

### 2. Start Using

```bash
cd /path/to/elevai-connect
claude
```

Try: "List all available Pulumi stacks"
Try: "What workshops are available"

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
✓ Deployment complete!
```

⚠️ **Important**: Manual approval is always required in your terminal for deployments.

### Check Configuration

```
> What's the monthly budget for production?

Claude: The current budget limit for production is $500.
```

## Safety Features

🔒 **Manual Approval Required**: The MCP server never uses `--yes` flag. You must review and approve all changes in your terminal, even when you tell Claude to proceed.

✅ **Auto-approved (read-only)**:
- Preview changes
- List stacks  
- Read configuration
- View outputs

❌ **Requires terminal confirmation**:
- Deploy (`pulumi up`)
- Destroy resources (`pulumi destroy`)

## Troubleshooting

### MCP server not found
```bash
ls /path/to/elevai-connect/mcp-server/dist/index.js
cd mcp-server && npm run build  # Rebuild if needed
```

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

**Happy deploying! 🚀**
