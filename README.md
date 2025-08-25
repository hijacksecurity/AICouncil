# AI Council 🏛️

An interactive multi-agent system featuring 6 AI personalities with distinct expertise areas, real tool capabilities through MCP server integration, and natural conversation flow.

## Features ✨

- **6 Unique AI Personalities** - Each based on iconic fictional characters
- **MCP Server Integration** - Real-world tool capabilities with fallback support
- **Natural Conversation Flow** - 1-3 agents respond based on relevance
- **Boss-Employee Dynamics** - Respectful to you, unfiltered between agents
- **Enhanced Context Management** - Intelligent conversation tracking
- **Visual Clarity** - Color-coded agents with clear speaker identification

## Meet Your Team 👥

- **🖥️ Gilfoyle** - Infrastructure Administrator (Silicon Valley) - AWS management, cost analysis
- **⚡ Judy** - DevOps Engineer (Cyberpunk 2077) - Kubernetes cluster management
- **🧪 Rick** - Backend Engineer (Rick and Morty) - API testing, DNS lookup
- **🕷️ Wednesday** - Frontend Developer (Wednesday Addams) - Web security analysis
- **🔒 Elliot** - Security Engineer (Mr. Robot) - Security scanning, vulnerability assessment
- **⚖️ Saul** - Project Manager (Better Call Saul) - Smooth talking, no tools needed

## Quick Start 🚀

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set your API key**:
   ```bash
   export ANTHROPIC_API_KEY='your-key-here'
   ```

3. **Run the council**:
   ```bash
   # Option 1: Global command (recommended)
   council
   
   # Option 2: Direct execution
   cd src && python run.py
   ```

## Global Command Setup 🔧

Install the `council` command globally:

```bash
# One-time setup - makes 'council' available anywhere
./council install

# Set your API key
export ANTHROPIC_API_KEY='your-key-here'

# Add to shell profile for permanent setup  
echo 'export ANTHROPIC_API_KEY="your-key-here"' >> ~/.bashrc  # or ~/.zshrc

# Run from anywhere
council
```

**Single file does it all:**
- `./council install` - Sets up global command
- `council` - Runs the application from anywhere
- Auto-detects project location, works for any user
- Optional `AICOUNCIL_HOME` environment variable for custom locations

## Usage Examples 💬

```
# Direct agent communication
@gilfoyle check our AWS costs this month
@judy what pods are running in production?
@all how should we scale our microservice?

# Natural conversation - agents auto-selected
"Our API is responding slowly"          # Rick + Judy respond
"Need security headers checked"         # Elliot + Wednesday respond  
"What's our infrastructure budget?"     # Gilfoyle responds solo
```

## MCP Server Enhancement 🔧

For full capabilities, install MCP servers:

```bash
# AWS management for Gilfoyle
npm install -g @modelcontextprotocol/server-aws

# Kubernetes management for Judy  
docker pull mcp-k8s-server
```

**Without MCP servers**: System gracefully falls back to traditional shell commands.

**With MCP servers**: Agents get rich, structured data and advanced capabilities.

## Architecture 🏗️

```
├── requirements.txt
├── .gitignore
├── README.md
├── CLAUDE.md
└── src/
    ├── run.py          # Application entry point
    └── aicouncil/
    ├── agents/         # Agent personalities and tool definitions
    ├── context/        # Conversation context management
    ├── tools/          # Shell + MCP tool execution
    ├── ui/             # Visual display management
    ├── models.py       # Core data structures
    ├── council.py      # Main orchestrator
    └── main.py         # Application entry point
```

## Contributing 🤝

1. Follow the existing agent personality patterns
2. Add MCP tools with shell fallbacks
3. Maintain character authenticity in tool result presentation
4. Keep responses concise (2 sentences max for business efficiency)

## License 📄

Built for educational and entertainment purposes. Character personalities are inspired by their respective fictional universes.

---

**"Better Call Saul... or better yet, call the whole council!"** ⚖️