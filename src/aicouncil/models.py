"""
Core data models for the AI Council system.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from enum import Enum
import hashlib


class ToolType(Enum):
    """Types of tools available to agents"""
    SHELL = "shell"
    MCP = "mcp"


@dataclass
class Tool:
    """Base tool that an agent can use"""
    name: str
    description: str
    tool_type: ToolType
    timeout: int = 30
    requires_confirmation: bool = False
    safe_mode: bool = True


@dataclass
class ShellTool(Tool):
    """Traditional shell command tool"""
    command_template: str = ""
    tool_type: ToolType = field(default=ToolType.SHELL, init=False)


@dataclass
class MCPTool(Tool):
    """MCP server-based tool with rich capabilities"""
    server_name: str = ""
    server_config: Dict[str, Any] = field(default_factory=dict)
    tool_schema: Dict[str, Any] = field(default_factory=dict)  # MCP tool schema
    tool_type: ToolType = field(default=ToolType.MCP, init=False)


@dataclass
class ToolResult:
    """Result from tool execution"""
    success: bool
    output: Union[str, Dict[str, Any]]  # Can be string or structured data
    error: Optional[str] = None
    execution_time: float = 0.0
    tool_type: ToolType = ToolType.SHELL
    raw_data: Optional[Dict[str, Any]] = None  # For MCP structured responses


@dataclass
class Agent:
    """Represents an AI agent with personality, tools, and capabilities"""
    name: str
    role: str
    color: str
    emoji: str
    triggers: List[str]
    personality: str
    catchphrases: List[str]
    interaction_style: str
    tools: List[Tool] = field(default_factory=list)
    relevance_weight: float = 1.0  # How likely to be selected


@dataclass
class Message:
    """Enhanced message structure with metadata"""
    content: str
    sender: str
    timestamp: datetime
    tokens: int = 0
    importance: float = 1.0
    summary: Optional[str] = None
    is_complete: bool = True
    continuation_of: Optional[str] = None  # ID of previous message if continued
    
    def get_id(self) -> str:
        """Generate unique message ID"""
        return hashlib.md5(f"{self.sender}{self.timestamp}{self.content[:50]}".encode()).hexdigest()[:8]