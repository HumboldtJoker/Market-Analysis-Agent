#!/usr/bin/env node

/**
 * MCP Server for Market Analysis Agent - Version 2
 * Robust implementation with better error handling
 */

console.log("MCP SERVER V2 STARTING");

// Load environment variables first
import 'dotenv/config';

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

console.log("All imports successful, dirname:", __dirname);

class MarketAnalysisServerV2 {
  constructor() {
    console.log("Creating server instance V2");
    this.server = new Server(
      {
        name: 'market-analysis-agent-v2',
        version: '2.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
    this.setupErrorHandling();
    console.log("Server V2 setup complete");
  }

  setupToolHandlers() {
    console.log("Setting up tool handlers V2");

    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      console.log("ListTools request received");
      return {
        tools: [
          {
            name: 'analyze_stock',
            description: 'Comprehensive stock analysis using AI-powered methodology',
            inputSchema: {
              type: 'object',
              properties: {
                ticker: {
                  type: 'string',
                  description: 'Stock symbol (e.g., AAPL, MSFT, TSLA)',
                },
                query: {
                  type: 'string',
                  description: 'Analysis query or question about the stock',
                  default: 'Should I invest in this stock? Provide a clear recommendation.',
                },
              },
              required: ['ticker'],
            },
          },
          {
            name: 'technical_analysis',
            description: 'Technical indicators analysis (SMA, RSI, MACD, Bollinger Bands)',
            inputSchema: {
              type: 'object',
              properties: {
                ticker: {
                  type: 'string',
                  description: 'Stock symbol for technical analysis',
                },
              },
              required: ['ticker'],
            },
          },
          {
            name: 'macro_analysis',
            description: 'Macro economic analysis and market regime detection',
            inputSchema: {
              type: 'object',
              properties: {},
            },
          },
          {
            name: 'test_connection',
            description: 'Test MCP connection and Python integration',
            inputSchema: {
              type: 'object',
              properties: {
                message: {
                  type: 'string',
                  description: 'Test message',
                  default: 'Connection test',
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
        switch (name) {
          case 'analyze_stock':
            return await this.analyzeStock(args);
          case 'technical_analysis':
            return await this.technicalAnalysis(args);
          case 'macro_analysis':
            return await this.macroAnalysis(args);
          case 'test_connection':
            return await this.testConnection(args);
          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        console.error(`Tool execution error for ${name}:`, error);
        return {
          content: [
            {
              type: 'text',
              text: `Error executing ${name}: ${error.message}\n\nFull error: ${error.stack}`,
            },
          ],
          isError: true,
        };
      }
    });

    console.log("Tool handlers V2 set up successfully");
  }

  async executePython(scriptName, args = []) {
    console.log(`Executing Python script: ${scriptName} with args:`, args);

    return new Promise((resolve, reject) => {
      const pythonPath = 'py'; // Use 'py' launcher on Windows
      const scriptPath = path.join(__dirname, scriptName);

      console.log(`Spawning: ${pythonPath} ${scriptPath} ${args.join(' ')}`);

      const process = spawn(pythonPath, [scriptPath, ...args], {
        cwd: __dirname,
        env: {
          ...process.env,
          PYTHONPATH: __dirname,
          FRED_API_KEY: process.env.FRED_API_KEY,
          ALPACA_API_KEY: process.env.ALPACA_API_KEY,
          ALPACA_SECRET_KEY: process.env.ALPACA_SECRET_KEY,
          ALPACA_BASE_URL: process.env.ALPACA_BASE_URL
        },
      });

      let stdout = '';
      let stderr = '';

      process.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      process.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      process.on('close', (code) => {
        console.log(`Python script finished with code: ${code}`);
        if (stderr) console.log(`Python stderr: ${stderr}`);

        if (code === 0) {
          resolve(stdout.trim());
        } else {
          reject(new Error(`Python script failed with code ${code}: ${stderr}`));
        }
      });

      process.on('error', (error) => {
        console.error(`Failed to start Python process: ${error.message}`);
        reject(new Error(`Failed to start Python process: ${error.message}`));
      });
    });
  }

  async testConnection(args) {
    const message = args.message || 'Connection test';
    console.log("Testing connection with message:", message);

    try {
      // Test Python execution
      const pythonResult = await this.executePython('test_connection.py', [message]);

      return {
        content: [
          {
            type: 'text',
            text: `✅ MCP Connection Test Successful!\n\nMessage: ${message}\nPython Response: ${pythonResult}\nTimestamp: ${new Date().toISOString()}`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: `⚠️ MCP Connection Test - Python execution failed: ${error.message}`,
          },
        ],
      };
    }
  }

  async analyzeStock(args) {
    const { ticker, query = 'Should I invest in this stock? Provide a clear recommendation.' } = args;
    console.log(`Analyzing stock: ${ticker} with query: ${query}`);

    try {
      const result = await this.executePython('mcp_wrapper.py', [
        'analyze_stock',
        ticker,
        query,
        'false'
      ]);

      return {
        content: [
          {
            type: 'text',
            text: result,
          },
        ],
      };
    } catch (error) {
      throw new Error(`Stock analysis failed: ${error.message}`);
    }
  }

  async technicalAnalysis(args) {
    const { ticker } = args;
    console.log(`Technical analysis for: ${ticker}`);

    try {
      const result = await this.executePython('mcp_wrapper.py', [
        'technical_analysis',
        ticker
      ]);

      return {
        content: [
          {
            type: 'text',
            text: result,
          },
        ],
      };
    } catch (error) {
      throw new Error(`Technical analysis failed: ${error.message}`);
    }
  }

  async macroAnalysis(args) {
    console.log("Running macro analysis");

    try {
      const result = await this.executePython('mcp_wrapper.py', [
        'macro_analysis'
      ]);

      return {
        content: [
          {
            type: 'text',
            text: result,
          },
        ],
      };
    } catch (error) {
      throw new Error(`Macro analysis failed: ${error.message}`);
    }
  }

  setupErrorHandling() {
    this.server.onerror = (error) => {
      console.error('[MCP Error]', error);
    };

    process.on('SIGINT', async () => {
      console.log("Received SIGINT, shutting down V2");
      await this.server.close();
      process.exit(0);
    });
  }

  async run() {
    console.log("Starting server connection V2");
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.log('Market Analysis Agent MCP server V2 running on stdio');
  }
}

// Create test connection script
import { writeFileSync } from 'fs';
const testScript = `#!/usr/bin/env python3
import sys
message = sys.argv[1] if len(sys.argv) > 1 else "Default test message"
print(f"Python connection test successful! Message: {message}")
`;

try {
  writeFileSync(path.join(__dirname, 'test_connection.py'), testScript);
  console.log("Created test_connection.py");
} catch (error) {
  console.error("Failed to create test_connection.py:", error);
}

// Initialize and run server
async function main() {
  try {
    console.log("Main function starting V2");
    const server = new MarketAnalysisServerV2();
    console.log("Server V2 created, calling run()");
    await server.run();
    console.log("Server V2 run() completed");
  } catch (error) {
    console.error("Fatal error in main V2:", error);
    process.exit(1);
  }
}

console.log("Calling main() V2");
main().catch((error) => {
  console.error("Uncaught error in V2:", error);
  process.exit(1);
});