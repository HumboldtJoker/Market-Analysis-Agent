#!/usr/bin/env node

/**
 * MCP Server for Market Analysis Agent - FIXED VERSION
 * Fixes the 'process' variable conflict and JSON logging issues
 */

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

class MarketAnalysisServer {
  constructor() {
    this.server = new Server(
      {
        name: 'market-analysis-agent',
        version: '1.0.0',
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

  setupToolHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: 'analyze_stock',
            description: 'Comprehensive stock analysis using AI-powered ReAct methodology with real-time data',
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
                include_profile: {
                  type: 'boolean',
                  description: 'Whether to include personalized investor profile in analysis',
                  default: false,
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
            name: 'portfolio_analysis',
            description: 'Portfolio correlation and diversification analysis',
            inputSchema: {
              type: 'object',
              properties: {
                tickers: {
                  type: 'array',
                  items: { type: 'string' },
                  description: 'Array of stock symbols in the portfolio',
                },
              },
              required: ['tickers'],
            },
          },
          {
            name: 'macro_analysis',
            description: 'Macro economic overlay and market regime detection',
            inputSchema: {
              type: 'object',
              properties: {},
            },
          },
        ],
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case 'analyze_stock':
            return await this.analyzeStock(args);
          case 'technical_analysis':
            return await this.technicalAnalysis(args);
          case 'portfolio_analysis':
            return await this.portfolioAnalysis(args);
          case 'macro_analysis':
            return await this.macroAnalysis(args);
          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
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
  }

  async executePython(scriptName, args = []) {
    return new Promise((resolve, reject) => {
      const pythonPath = 'py'; // Use 'py' launcher on Windows
      const scriptPath = path.join(__dirname, scriptName);

      // FIXED: Rename 'process' variable to avoid conflict
      const childProcess = spawn(pythonPath, [scriptPath, ...args], {
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

      childProcess.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      childProcess.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      childProcess.on('close', (code) => {
        if (code === 0) {
          resolve(stdout.trim());
        } else {
          reject(new Error(`Python script failed with code ${code}: ${stderr}`));
        }
      });

      childProcess.on('error', (error) => {
        reject(new Error(`Failed to start Python process: ${error.message}`));
      });
    });
  }

  async analyzeStock(args) {
    const { ticker, query = 'Should I invest in this stock? Provide a clear recommendation.', include_profile = false } = args;

    try {
      const result = await this.executePython('mcp_wrapper.py', [
        'analyze_stock',
        ticker,
        query,
        include_profile.toString()
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

  async portfolioAnalysis(args) {
    const { tickers } = args;

    try {
      const result = await this.executePython('mcp_wrapper.py', [
        'portfolio_analysis',
        JSON.stringify(tickers)
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
      throw new Error(`Portfolio analysis failed: ${error.message}`);
    }
  }

  async macroAnalysis(args) {
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
      await this.server.close();
      process.exit(0);
    });
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    // FIXED: Use stderr for logging, stdout is for MCP JSON
    console.error('Market Analysis Agent MCP server running on stdio');
  }
}

// Initialize and run server
async function main() {
  const server = new MarketAnalysisServer();
  await server.run();
}

main().catch(console.error);