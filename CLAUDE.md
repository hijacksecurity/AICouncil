# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AICouncil is an interactive multi-agent system that simulates a development team with 6 distinct AI personalities. Each agent has specialized expertise and responds in character based on popular fiction characters. The system now features **MCP (Model Context Protocol) server integration** for advanced real-world capabilities.

## Repository Structure

```
AICouncil/
├── requirements.txt            # Dependencies including MCP
├── .gitignore                 # Comprehensive gitignore
├── README.md                  # Public documentation
├── CLAUDE.md                  # This documentation
└── src/                        # All source code
    ├── run.py                  # Application entry point
    └── aicouncil/              # Main package
    ├── __init__.py
    ├── main.py                 # Application entry point with async MCP support
    ├── models.py               # Core data models (Tool, Agent, Message)
    ├── council.py              # Main orchestrator
    ├── agents/
    │   ├── __init__.py
    │   ├── definitions.py      # Agent personalities and MCP tools
    │   ├── response_manager.py # Response generation with tool integration
    │   └── selector.py         # Agent selection logic
    ├── context/
    │   ├── __init__.py
    │   └── manager.py          # Conversation context management
    ├── tools/
    │   ├── __init__.py
    │   ├── manager.py          # Shell + MCP tool execution
    │   └── mcp_manager.py      # MCP server integration
    └── ui/
        ├── __init__.py
        └── display.py          # Visual display management
```

## Prerequisites

- Python 3.8+ (required for MCP async support)
- Anthropic API key
- MCP server installations (optional, falls back to shell tools)
- Virtual environment recommended

## Architecture

The system now uses a modular architecture with MCP server integration:

### Core Components
- **Council**: Main orchestrator managing agent interactions and conversation flow
- **Agent Models**: Enhanced with both Shell and MCP tool support
- **Tool System**: Dual-mode execution (traditional shell + MCP servers)
- **Context Manager**: Intelligent conversation context with complexity tracking
- **Response Manager**: Handles tool integration and response completion

### 6 Enhanced AI Agents
Each agent now has both traditional shell tools AND MCP server capabilities:

- **🖥️ Gilfoyle** (Infrastructure): AWS MCP server + shell fallbacks
- **⚡ Judy** (DevOps): Kubernetes MCP server + kubectl fallbacks  
- **🧪 Rick** (Backend): API testing + shell utilities
- **🕷️ Wednesday** (Frontend): Web security analysis tools
- **🔒 Elliot** (Security): Security scanning + DNS enumeration
- **⚖️ Saul** (Project Manager): Pure charm (no tools needed)

### MCP Integration Features
- **Async Tool Execution**: Full async/await support for MCP servers
- **Rich Structured Data**: MCP tools return detailed, structured information
- **Fallback Safety**: Graceful degradation to shell tools if MCP servers unavailable
- **Character Integration**: Tool results are presented in each agent's unique personality

## Setup & Installation

```bash
# Clone the repository
git clone <repository-url>
cd AICouncil

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variable (required)
export ANTHROPIC_API_KEY='your-key-here'  # On Windows: set ANTHROPIC_API_KEY=your-key-here

# Install globally (one-time setup)
./council install

# Run the interactive council with MCP support
council
```

## Global Command Setup

The `council` script automatically:
- Auto-detects project location (no hardcoded paths)
- Detects and activates the virtual environment
- Checks for required API key
- Runs from the correct directory
- Provides helpful error messages
- Works for any user without configuration

**Installation for any user:**
```bash
# Single command installation
./council install

# Add API key to your shell profile
echo 'export ANTHROPIC_API_KEY="your-key-here"' >> ~/.bashrc  # or ~/.zshrc
source ~/.bashrc  # or restart terminal

# Optional: Set custom project location
echo 'export AICOUNCIL_HOME="/your/custom/path"' >> ~/.bashrc

# Now run from anywhere
council
```

## MCP Server Setup (Optional but Recommended)

To unlock full capabilities, install MCP servers for each agent:

```bash
# Gilfoyle's AWS MCP Server
npm install -g @modelcontextprotocol/server-aws

# Judy's Kubernetes MCP Server (requires Docker)
docker pull mcp-k8s-server

# Additional MCP servers can be configured in tools/mcp_manager.py
```

## Git Workflow

```bash
# Initial setup for pushing to remote
git init
git add .
git commit -m "Initial commit: AI Council multi-agent system"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main

# Regular development workflow
git add .
git commit -m "feat: description of changes"
git push
```

## In-App Commands

- `exit` - End the session
- `reset` - Clear conversation history  
- `help` - Show available commands
- `@<agent_name> <message>` - Direct message to specific agent
- `@all <message>` - Message all agents

## API Usage

The system uses two Claude models:
- **claude-opus-4-1-20250805**: Main agent responses (line 247)
- **claude-3-haiku-20240307**: Quick decisions for agent relevance and interjections (lines 192, 219, 269)

## Development Notes

### Code Organization
- **src/aicouncil/agents/definitions.py**: Agent personalities with MCP + shell tools
- **src/aicouncil/tools/mcp_manager.py**: MCP server configurations and client management
- **src/aicouncil/models.py**: Enhanced models supporting both ToolType.SHELL and ToolType.MCP
- **src/run.py**: Application entry point
- **src/aicouncil/main.py**: Async main function with proper MCP cleanup

### Key Features
- **Dual Tool System**: MCP servers with shell tool fallbacks
- **Natural Conversation**: 1-3 agent selection based on relevance scoring
- **Enhanced Context**: Dynamic window sizing (5-15 messages) based on complexity
- **Boss-Employee Dynamics**: Respectful to user, unfiltered between agents
- **Response Completion**: Auto-continuation for incomplete responses
- **Character Consistency**: Tool results integrated into each agent's personality

### MCP Integration Details
- **Async Support**: Full async/await pattern for MCP server communication
- **JSON-RPC Protocol**: Standard MCP protocol implementation
- **Server Lifecycle**: Automatic connection management and cleanup
- **Error Handling**: Graceful fallback to shell tools on MCP failures
- **Structured Data**: Rich tool results with raw_data preservation

### Performance Considerations
- **Event Loop Management**: Careful async loop handling for MCP integration
- **Connection Pooling**: MCP clients are reused across tool executions
- **Timeout Handling**: Both MCP and shell tools have configurable timeouts
- **Memory Management**: Proper cleanup of async resources

## Important Files

- **DO NOT COMMIT**: API keys, `.env` files, or `secrets.json`
- **Virtual Environment**: `.venv/` is ignored and should not be committed
- **IDE Files**: `.idea/` (PyCharm), `.vscode/`, and other IDE configs are ignored
- **MCP Servers**: External MCP server installations not tracked in repo
- Working basic tools - update documentation