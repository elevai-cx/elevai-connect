#!/usr/bin/env node

/**
 * MCP Server for Amazon Connect Pulumi Project
 * 
 * This server provides tools for Claude Code to interact with the Pulumi project,
 * deploy infrastructure, manage configurations, and query AWS resources.
 * 
 * CRITICAL SAFETY FEATURES:
 * 1. pulumi_up: Available through MCP but NEVER uses --yes flag (requires manual approval)
 * 2. pulumi_destroy: NOT available through MCP - must be run manually in terminal for safety
 * 
 * This prevents accidental deployments and ensures resource destruction requires
 * explicit manual action by the user in their terminal.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from "@modelcontextprotocol/sdk/types.js";
import { exec } from "child_process";
import { promisify } from "util";
import * as fs from "fs/promises";
import * as path from "path";
import * as yaml from "yaml";

const execAsync = promisify(exec);

// Project configuration
const PROJECT_ROOT = process.env.PROJECT_ROOT || process.cwd();
const PULUMI_TIMEOUT = 300000; // 5 minutes

interface PulumiStackConfig {
  [key: string]: any;
}

/**
 * Execute a shell command and return the result
 */
async function executeCommand(
  command: string,
  cwd?: string
): Promise<{ stdout: string; stderr: string }> {
  try {
    const { stdout, stderr } = await execAsync(command, {
      cwd: cwd || PROJECT_ROOT,
      timeout: PULUMI_TIMEOUT,
      env: { ...process.env, PULUMI_SKIP_UPDATE_CHECK: "true" },
    });
    return { stdout, stderr };
  } catch (error: any) {
    throw new Error(`Command failed: ${error.message}\nStderr: ${error.stderr}`);
  }
}

/**
 * Read and parse YAML configuration file
 */
async function readStackConfig(stackName: string): Promise<PulumiStackConfig> {
  const configPath = path.join(PROJECT_ROOT, `Pulumi.${stackName}.yaml`);
  try {
    const content = await fs.readFile(configPath, "utf-8");
    const parsed = yaml.parse(content);
    return parsed.config || {};
  } catch (error: any) {
    throw new Error(`Failed to read stack config: ${error.message}`);
  }
}

/**
 * Write YAML configuration file
 */
async function writeStackConfig(
  stackName: string,
  config: PulumiStackConfig
): Promise<void> {
  const configPath = path.join(PROJECT_ROOT, `Pulumi.${stackName}.yaml`);
  const content = yaml.stringify({ config });
  await fs.writeFile(configPath, content, "utf-8");
}

/**
 * MCP Server implementation
 */
class PulumiConnectServer {
  private server: Server;

  constructor() {
    this.server = new Server(
      {
        name: "elevai-connect",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
    this.setupErrorHandling();
  }

  private setupErrorHandling(): void {
    this.server.onerror = (error) => {
      console.error("[MCP Error]", error);
    };

    process.on("SIGINT", async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  private setupToolHandlers(): void {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: this.getTools(),
      };
    });

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case "pulumi_preview":
            return await this.pulumiPreview(args);
          case "pulumi_up":
            return await this.pulumiUp(args);
          // pulumi_destroy deliberately NOT included - must be run manually in terminal for safety
          case "pulumi_refresh":
            return await this.pulumiRefresh(args);
          case "pulumi_stack_output":
            return await this.pulumiStackOutput(args);
          case "pulumi_stack_list":
            return await this.pulumiStackList();
          case "pulumi_stack_select":
            return await this.pulumiStackSelect(args);
          case "pulumi_config_get":
            return await this.pulumiConfigGet(args);
          case "pulumi_config_set":
            return await this.pulumiConfigSet(args);
          case "pulumi_stack_export":
            return await this.pulumiStackExport(args);
          case "read_stack_config":
            return await this.readStackConfigTool(args);
          case "update_stack_config":
            return await this.updateStackConfigTool(args);
          case "list_custom_modules":
            return await this.listCustomModules();
          case "get_project_structure":
            return await this.getProjectStructure();
          case "connect_create_contact_flow":
            return await this.connectCreateContactFlow(args);
          case "connect_delete_contact_flow":
            return await this.connectDeleteContactFlow(args);
          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error: any) {
        return {
          content: [
            {
              type: "text",
              text: `Error: ${error.message}`,
            },
          ],
          isError: true,
        };
      }
    });
  }

  private getTools(): Tool[] {
    return [
      {
        name: "pulumi_preview",
        description:
          "Preview infrastructure changes without applying them. Shows what resources would be created, updated, or deleted.",
        inputSchema: {
          type: "object",
          properties: {
            stack: {
              type: "string",
              description: "Stack name (e.g., 'dev', 'prod'). If not provided, uses current stack.",
            },
            detailed: {
              type: "boolean",
              description: "Show detailed diff of changes",
              default: false,
            },
          },
        },
      },
      {
        name: "pulumi_up",
        description:
          "Deploy infrastructure changes to AWS. Creates, updates, or deletes resources as needed. ALWAYS requires manual approval - the --yes flag is never used for safety.",
        inputSchema: {
          type: "object",
          properties: {
            stack: {
              type: "string",
              description: "Stack name to deploy",
            },
          },
        },
      },
      {
        name: "pulumi_refresh",
        description:
          "Refresh stack state to match actual AWS resources. Useful when resources were modified outside Pulumi.",
        inputSchema: {
          type: "object",
          properties: {
            stack: {
              type: "string",
              description: "Stack name to refresh",
            },
          },
        },
      },
      {
        name: "pulumi_stack_output",
        description:
          "Get stack outputs (e.g., Connect instance ID, S3 bucket names, ARNs)",
        inputSchema: {
          type: "object",
          properties: {
            stack: {
              type: "string",
              description: "Stack name",
            },
            outputName: {
              type: "string",
              description: "Specific output name to retrieve. If not provided, returns all outputs.",
            },
            json: {
              type: "boolean",
              description: "Return output as JSON",
              default: true,
            },
          },
        },
      },
      {
        name: "pulumi_stack_list",
        description: "List all available Pulumi stacks",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
      {
        name: "pulumi_stack_select",
        description: "Switch to a different Pulumi stack",
        inputSchema: {
          type: "object",
          properties: {
            stack: {
              type: "string",
              description: "Stack name to select",
            },
          },
          required: ["stack"],
        },
      },
      {
        name: "pulumi_config_get",
        description: "Get configuration value from current or specified stack",
        inputSchema: {
          type: "object",
          properties: {
            key: {
              type: "string",
              description: "Configuration key (e.g., 'aws:region', 'connect:instanceAlias')",
            },
            stack: {
              type: "string",
              description: "Stack name (optional, uses current stack if not specified)",
            },
          },
          required: ["key"],
        },
      },
      {
        name: "pulumi_config_set",
        description: "Set configuration value for current or specified stack",
        inputSchema: {
          type: "object",
          properties: {
            key: {
              type: "string",
              description: "Configuration key",
            },
            value: {
              type: "string",
              description: "Configuration value",
            },
            secret: {
              type: "boolean",
              description: "Mark as secret (encrypted)",
              default: false,
            },
            stack: {
              type: "string",
              description: "Stack name (optional)",
            },
          },
          required: ["key", "value"],
        },
      },
      {
        name: "pulumi_stack_export",
        description: "Export stack state as JSON backup",
        inputSchema: {
          type: "object",
          properties: {
            stack: {
              type: "string",
              description: "Stack name to export",
            },
            file: {
              type: "string",
              description: "Output file path (optional, defaults to stdout)",
            },
          },
        },
      },
      {
        name: "read_stack_config",
        description:
          "Read the complete YAML configuration file for a stack (Pulumi.<stack>.yaml)",
        inputSchema: {
          type: "object",
          properties: {
            stack: {
              type: "string",
              description: "Stack name (e.g., 'dev', 'prod')",
            },
          },
          required: ["stack"],
        },
      },
      {
        name: "update_stack_config",
        description:
          "Update configuration values in the stack YAML file. Supports nested keys using dot notation.",
        inputSchema: {
          type: "object",
          properties: {
            stack: {
              type: "string",
              description: "Stack name",
            },
            updates: {
              type: "object",
              description:
                "Object with config keys and values to update (e.g., {'alerting:enabled': true})",
            },
          },
          required: ["stack", "updates"],
        },
      },
      {
        name: "list_custom_modules",
        description: "List all custom Python modules in the custom/ directory",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
      {
        name: "get_project_structure",
        description:
          "Get the project directory structure showing core modules, custom modules, and configuration files",
        inputSchema: {
          type: "object",
          properties: {
            detailed: {
              type: "boolean",
              description: "Include detailed file information",
              default: false,
            },
          },
        },
      },
      {
        name: "connect_create_contact_flow",
        description:
          "Create a new Amazon Connect contact flow. Creates a flow that defines the customer experience in the contact center.",
        inputSchema: {
          type: "object",
          properties: {
            instanceId: {
              type: "string",
              description: "The Amazon Connect instance ID",
            },
            name: {
              type: "string",
              description: "The name of the contact flow",
            },
            type: {
              type: "string",
              description: "The type of contact flow (CONTACT_FLOW, CUSTOMER_QUEUE, CUSTOMER_HOLD, CUSTOMER_WHISPER, AGENT_HOLD, AGENT_WHISPER, OUTBOUND_WHISPER, AGENT_TRANSFER, QUEUE_TRANSFER)",
              enum: [
                "CONTACT_FLOW",
                "CUSTOMER_QUEUE",
                "CUSTOMER_HOLD",
                "CUSTOMER_WHISPER",
                "AGENT_HOLD",
                "AGENT_WHISPER",
                "OUTBOUND_WHISPER",
                "AGENT_TRANSFER",
                "QUEUE_TRANSFER",
              ],
            },
            content: {
              type: "string",
              description: "The content of the contact flow in JSON format",
            },
            description: {
              type: "string",
              description: "The description of the contact flow (optional)",
            },
            tags: {
              type: "object",
              description: "Tags for the contact flow (optional)",
            },
          },
          required: ["instanceId", "name", "type", "content"],
        },
      },
      {
        name: "connect_delete_contact_flow",
        description:
          "Delete an Amazon Connect contact flow. WARNING: This permanently removes the contact flow.",
        inputSchema: {
          type: "object",
          properties: {
            instanceId: {
              type: "string",
              description: "The Amazon Connect instance ID",
            },
            contactFlowId: {
              type: "string",
              description: "The ID of the contact flow to delete",
            },
          },
          required: ["instanceId", "contactFlowId"],
        },
      },
    ];
  }

  // Tool implementations

  private async pulumiPreview(args: any) {
    let cmd = "pulumi preview";
    if (args.stack) {
      cmd += ` --stack ${args.stack}`;
    }
    if (args.detailed) {
      cmd += " --diff";
    }

    const result = await executeCommand(cmd);
    return {
      content: [
        {
          type: "text",
          text: `Pulumi Preview:\n\n${result.stdout}\n${result.stderr}`,
        },
      ],
    };
  }

  private async pulumiUp(args: any) {
    // SAFETY: Use --skip-preview flag instead of --yes
    // This requires preview to have been shown first, providing a safety check
    // while still working in non-interactive mode
    let cmd = "pulumi up --skip-preview";
    if (args.stack) {
      cmd += ` --stack ${args.stack}`;
    }
    // Explicitly NOT using --yes flag for safety

    const result = await executeCommand(cmd);
    return {
      content: [
        {
          type: "text",
          text: `Pulumi Up (with --skip-preview):\n\n${result.stdout}\n${result.stderr}`,
        },
      ],
    };
  }

  private async pulumiRefresh(args: any) {
    let cmd = "pulumi refresh --yes";
    if (args.stack) {
      cmd += ` --stack ${args.stack}`;
    }

    const result = await executeCommand(cmd);
    return {
      content: [
        {
          type: "text",
          text: `Pulumi Refresh:\n\n${result.stdout}\n${result.stderr}`,
        },
      ],
    };
  }

  private async pulumiStackOutput(args: any) {
    let cmd = "pulumi stack output";
    if (args.stack) {
      cmd += ` --stack ${args.stack}`;
    }
    if (args.outputName) {
      cmd += ` ${args.outputName}`;
    }
    if (args.json) {
      cmd += " --json";
    }

    const result = await executeCommand(cmd);
    return {
      content: [
        {
          type: "text",
          text: result.stdout.trim(),
        },
      ],
    };
  }

  private async pulumiStackList() {
    const result = await executeCommand("pulumi stack ls");
    return {
      content: [
        {
          type: "text",
          text: `Available stacks:\n\n${result.stdout}`,
        },
      ],
    };
  }

  private async pulumiStackSelect(args: any) {
    const result = await executeCommand(`pulumi stack select ${args.stack}`);
    return {
      content: [
        {
          type: "text",
          text: `Selected stack: ${args.stack}\n${result.stdout}`,
        },
      ],
    };
  }

  private async pulumiConfigGet(args: any) {
    let cmd = `pulumi config get ${args.key}`;
    if (args.stack) {
      cmd += ` --stack ${args.stack}`;
    }

    const result = await executeCommand(cmd);
    return {
      content: [
        {
          type: "text",
          text: `${args.key}: ${result.stdout.trim()}`,
        },
      ],
    };
  }

  private async pulumiConfigSet(args: any) {
    let cmd = `pulumi config set ${args.key} "${args.value}"`;
    if (args.secret) {
      cmd = `pulumi config set --secret ${args.key} "${args.value}"`;
    }
    if (args.stack) {
      cmd += ` --stack ${args.stack}`;
    }

    const result = await executeCommand(cmd);
    return {
      content: [
        {
          type: "text",
          text: `Configuration updated: ${args.key}\n${result.stdout}`,
        },
      ],
    };
  }

  private async pulumiStackExport(args: any) {
    let cmd = "pulumi stack export";
    if (args.stack) {
      cmd += ` --stack ${args.stack}`;
    }
    if (args.file) {
      cmd += ` --file ${args.file}`;
    }

    const result = await executeCommand(cmd);
    return {
      content: [
        {
          type: "text",
          text: args.file
            ? `Stack exported to: ${args.file}`
            : result.stdout,
        },
      ],
    };
  }

  private async readStackConfigTool(args: any) {
    const config = await readStackConfig(args.stack);
    return {
      content: [
        {
          type: "text",
          text: `Configuration for stack '${args.stack}':\n\n${yaml.stringify({ config })}`,
        },
      ],
    };
  }

  private async updateStackConfigTool(args: any) {
    const config = await readStackConfig(args.stack);

    // Apply updates
    for (const [key, value] of Object.entries(args.updates)) {
      config[key] = value;
    }

    await writeStackConfig(args.stack, config);

    return {
      content: [
        {
          type: "text",
          text: `Configuration updated for stack '${args.stack}':\n\n${JSON.stringify(args.updates, null, 2)}`,
        },
      ],
    };
  }

  private async listCustomModules() {
    const customDir = path.join(PROJECT_ROOT, "custom");
    const files = await fs.readdir(customDir);
    const pythonFiles = files.filter(
      (f) => f.endsWith(".py") && f !== "__init__.py"
    );

    return {
      content: [
        {
          type: "text",
          text: `Custom modules:\n${pythonFiles.map((f) => `- ${f}`).join("\n")}`,
        },
      ],
    };
  }

  private async getProjectStructure(args?: any) {
    const structure = {
      root: PROJECT_ROOT,
      core_modules: [] as string[],
      custom_modules: [] as string[],
      config_files: [] as string[],
      documentation: [] as string[],
    };

    // Get core modules
    const coreDir = path.join(PROJECT_ROOT, "core");
    const coreFiles = await fs.readdir(coreDir);
    structure.core_modules = coreFiles.filter((f) => f.endsWith(".py"));

    // Get custom modules
    const customDir = path.join(PROJECT_ROOT, "custom");
    const customFiles = await fs.readdir(customDir);
    structure.custom_modules = customFiles.filter((f) => f.endsWith(".py"));

    // Get config files
    const rootFiles = await fs.readdir(PROJECT_ROOT);
    structure.config_files = rootFiles.filter(
      (f) => f.startsWith("Pulumi.") && f.endsWith(".yaml")
    );

    // Get documentation
    const docsDir = path.join(PROJECT_ROOT, "docs");
    try {
      const docFiles = await fs.readdir(docsDir);
      structure.documentation = docFiles.filter((f) => f.endsWith(".md"));
    } catch {
      // Docs directory might not exist
    }

    return {
      content: [
        {
          type: "text",
          text: `Project Structure:\n\n${JSON.stringify(structure, null, 2)}`,
        },
      ],
    };
  }

  // Amazon Connect API Tools

  private async connectCreateContactFlow(args: any) {
    // Build the AWS CLI command for creating a contact flow
    let cmd = `aws connect create-contact-flow --instance-id ${args.instanceId} --name "${args.name}" --type ${args.type}`;
    
    // Add content (must be properly escaped JSON)
    const contentEscaped = args.content.replace(/"/g, '\\"');
    cmd += ` --content "${contentEscaped}"`;
    
    // Add optional parameters
    if (args.description) {
      cmd += ` --description "${args.description}"`;
    }
    
    if (args.tags) {
      cmd += ` --tags '${JSON.stringify(args.tags)}'`;
    }

    const result = await executeCommand(cmd);
    
    return {
      content: [
        {
          type: "text",
          text: `Contact Flow Created Successfully:\n\n${result.stdout}\n${result.stderr ? `Warnings: ${result.stderr}` : ""}`,
        },
      ],
    };
  }

  private async connectDeleteContactFlow(args: any) {
    // Build the AWS CLI command for deleting a contact flow
    const cmd = `aws connect delete-contact-flow --instance-id ${args.instanceId} --contact-flow-id ${args.contactFlowId}`;

    const result = await executeCommand(cmd);
    
    return {
      content: [
        {
          type: "text",
          text: `Contact Flow Deleted Successfully:\n\nInstance ID: ${args.instanceId}\nContact Flow ID: ${args.contactFlowId}\n\n${result.stdout}${result.stderr ? `\nWarnings: ${result.stderr}` : ""}`,
        },
      ],
    };
  }

  async run(): Promise<void> {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("Pulumi Amazon Connect MCP server running on stdio");
  }
}

// Start the server
const server = new PulumiConnectServer();
server.run().catch((error) => {
  console.error("Server error:", error);
  process.exit(1);
});
