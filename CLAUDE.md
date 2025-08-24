# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AICouncil is an interactive multi-agent system that simulates a development team with 6 distinct AI personalities. Each agent has specialized expertise and responds in character based on popular fiction characters.

## Repository Structure

```
AICouncil/
├── council.py          # Main application file
├── .gitignore         # Comprehensive gitignore for Python/IDEs
├── .venv/             # Virtual environment (not tracked)
└── CLAUDE.md          # This documentation file
```

## Prerequisites

- Python 3.7+
- Anthropic API key
- Virtual environment recommended

## Architecture

The system consists of a single `council.py` file implementing:
- **Council class**: Main orchestrator that manages agent interactions and conversation flow
- **Agent dataclass**: Defines each team member's personality, triggers, and interaction style
- **6 Pre-configured Agents**:
  - Gilfoyle: Infrastructure/Cloud (Silicon Valley)
  - Judy: DevOps/Kubernetes (Cyberpunk 2077)
  - Rick: Backend/APIs (Rick and Morty)
  - Wednesday: Frontend/UI (Wednesday Addams)
  - Elliot: Security (Mr. Robot)
  - Saul: Project Management (Better Call Saul)

## Key Functionality

- **Agent Detection**: Automatically selects relevant agents based on keyword triggers or Claude API analysis
- **Conversation Management**: Maintains conversation history and allows agents to interject
- **Direct Messaging**: Support for @mentions to specific agents or @all
- **Inter-agent Banter**: Agents can comment on each other's responses (30% chance)

## Setup & Installation

```bash
# Clone the repository
git clone <repository-url>
cd AICouncil

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install anthropic colorama

# Set up environment variable (required)
export ANTHROPIC_API_KEY='your-key-here'  # On Windows: set ANTHROPIC_API_KEY=your-key-here

# Run the interactive council
python council.py
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

- Agent personalities are defined in lines 294-418 with BUSINESS MODE constraints
- Trigger keywords determine automatic agent activation
- Response length optimized to 400 tokens for concise business communication
- Maximum 2-sentence responses enforced for business efficiency
- Enhanced visual formatting with colored headers and separators
- Persistent color coding throughout each agent's response
- Agent interjections have 30% chance when not already active

## Visual Enhancements

- Colored separators distinguish each speaker clearly
- Agent headers show emoji, name, and role with consistent coloring
- Interjections marked with special "┈┈┈ [INTERJECTION] ┈┈┈" formatting
- Context status displayed with visual separators
- Enhanced user input prompt with green arrows

## Important Files

- **DO NOT COMMIT**: API keys, `.env` files, or `secrets.json`
- **Virtual Environment**: `.venv/` is ignored and should not be committed
- **IDE Files**: `.idea/` (PyCharm), `.vscode/`, and other IDE configs are ignored
- **Logs**: Any `*.log` files or `logs/` directories are ignored