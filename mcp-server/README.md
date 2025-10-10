# Pulumi Amazon Connect MCP Server

This Model Context Protocol (MCP) server enables Claude Code to interact with your Pulumi Amazon Connect infrastructure project.

## Quick Start

```bash
# Install dependencies
npm install

# Build the server
npm run build

# Verify it works
node dist/index.js
```

## Configuration

The server is configured in the project root's `.mcp.json` file. 

```json
{
  "mcpServers": {
    "elevai-connect": {
      "command": "node",
      "args": ["/absolute/path/to/elevai-connect/mcp-server/dist/index.js"],
      "env": {
        "PROJECT_ROOT": "/absolute/path/to/elevai-connect",
        "PULUMI_SKIP_UPDATE_CHECK": "true"
      },
      "autoApprove": [
        "pulumi_preview",
        "pulumi_stack_list",
        "pulumi_stack_output",
        "pulumi_config_get",
        "read_stack_config",
        "list_custom_modules",
        "get_project_structure"
      ]
    }
  }
}
```

## Available Tools

### Deployment
- `pulumi_preview` - Preview changes
- `pulumi_up` - Deploy infrastructure
- `pulumi_destroy` - Destroy resources (⚠️ requires manual approval)
- `pulumi_refresh` - Sync state

**Safety Feature**:  `pulumi_destroy` NEVER use the `--yes` flag. Users must always manually approve changes in their terminal.

### Configuration
- `pulumi_config_get` - Get config value
- `pulumi_config_set` - Set config value  
- `read_stack_config` - Read YAML config
- `update_stack_config` - Update YAML config

### Stack Management
- `pulumi_stack_list` - List stacks
- `pulumi_stack_select` - Switch stacks
- `pulumi_stack_output` - Get outputs
- `pulumi_stack_export` - Export state

### Project
- `list_custom_modules` - List custom extensions
- `get_project_structure` - Get project layout

## Development

```bash
# Watch mode for development
npm run watch

# Build for production
npm run build
```

## Documentation

For full setup instructions and usage examples, see:
- User guide: `../docs/CLAUDE_CODE_SETUP.md`
- Project context: `../Claude.md`

## License

Apache License 2.0 - See LICENSE file in project root.
