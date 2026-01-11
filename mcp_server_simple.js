#!/usr/bin/env node

/**
 * Simple MCP Server for Market Analysis Agent
 * Minimal implementation to debug initialization issues
 */

console.log("SIMPLE MCP SERVER STARTING - VERSION 1");

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

console.log("Imports successful");

class SimpleMarketAnalysisServer {
  constructor() {
    console.log("Creating server instance");
    this.server = new Server(
      {
        name: 'market-analysis-agent-simple',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    console.log("Server instance created, setting up handlers");
    this.setupToolHandlers();
    this.setupErrorHandling();
    console.log("Setup complete");
  }

  setupToolHandlers() {
    console.log("Setting up tool handlers");

    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      console.log("ListTools request received");
      return {
        tools: [
          {
            name: 'test_tool',
            description: 'Simple test tool to verify MCP connection',
            inputSchema: {
              type: 'object',
              properties: {
                message: {
                  type: 'string',
                  description: 'Test message',
                  default: 'Hello from MCP!',
                },
              },
            },
          },
        ],
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      console.log("CallTool request received:", request.params.name);

      const { name, arguments: args } = request.params;

      try {
        if (name === 'test_tool') {
          const message = args.message || 'Hello from MCP!';
          return {
            content: [
              {
                type: 'text',
                text: `Test tool executed successfully!\nMessage: ${message}\nTimestamp: ${new Date().toISOString()}`,
              },
            ],
          };
        } else {
          throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        console.error("Tool execution error:", error);
        return {
          content: [
            {
              type: 'text',
              text: `Error executing ${name}: ${error.message}`,
            },
          ],
          isError: true,
        };
      }
    });

    console.log("Tool handlers set up successfully");
  }

  setupErrorHandling() {
    this.server.onerror = (error) => {
      console.error('[MCP Error]', error);
    };

    process.on('SIGINT', async () => {
      console.log("Received SIGINT, shutting down");
      await this.server.close();
      process.exit(0);
    });
  }

  async run() {
    console.log("Starting server connection");
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.log('Simple Market Analysis Agent MCP server running on stdio');
  }
}

// Initialize and run server
async function main() {
  try {
    console.log("Main function starting");
    const server = new SimpleMarketAnalysisServer();
    console.log("Server created, calling run()");
    await server.run();
    console.log("Server.run() completed");
  } catch (error) {
    console.error("Fatal error in main:", error);
    process.exit(1);
  }
}

console.log("Calling main()");
main().catch((error) => {
  console.error("Uncaught error:", error);
  process.exit(1);
});