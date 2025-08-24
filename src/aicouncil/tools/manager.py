"""
Tool execution manager with security and timeout handling.
Supports both traditional shell commands and MCP server integration.
"""
import asyncio
import re
import shlex
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any, Dict

from ..models import Tool, ShellTool, MCPTool, ToolResult, ToolType
from .mcp_manager import MCPToolManager


class ToolManager:
    """Manages secure tool execution for agents (both shell and MCP)"""
    
    def __init__(self):
        # Shell command execution
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.safe_commands = {
            'aws': True,
            'kubectl': True, 
            'curl': True,
            'dig': True,
            'nslookup': True
        }
        # Whitelist of allowed command patterns
        self.allowed_patterns = [
            r'^aws (--version|sts get-caller-identity|ec2 describe-regions).*',
            r'^kubectl (version|get pods|get nodes|cluster-info).*',
            r'^curl -s -I https?://.*',
            r'^dig [a-zA-Z0-9.-]+ ?.*',
            r'^nslookup [a-zA-Z0-9.-]+.*'
        ]
        
        # MCP server integration
        self.mcp_manager = MCPToolManager()
        self.loop = None
    
    def execute_tool(self, tool: Tool, args: Dict[str, str]) -> ToolResult:
        """Execute a tool safely with timeout and validation"""
        if tool.tool_type == ToolType.MCP:
            return self._execute_mcp_tool(tool, args)
        else:
            return self._execute_shell_tool(tool, args)
    
    def _execute_mcp_tool(self, tool: MCPTool, args: Dict[str, str]) -> ToolResult:
        """Execute MCP tool with async handling"""
        try:
            # Ensure we have an event loop
            if self.loop is None or self.loop.is_closed():
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
            
            # Run the async MCP tool execution
            return self.loop.run_until_complete(
                self.mcp_manager.execute_mcp_tool(tool, args)
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"MCP execution error: {str(e)}",
                tool_type=ToolType.MCP
            )
    
    def _execute_shell_tool(self, tool: ShellTool, args: Dict[str, str]) -> ToolResult:
        """Execute traditional shell command tool"""
        start_time = time.time()
        
        try:
            # Format command with arguments
            command = tool.command_template.format(**args)
            
            # Validate command safety
            if tool.safe_mode and not self._is_safe_command(command):
                return ToolResult(
                    success=False,
                    output="",
                    error="Command not allowed in safe mode",
                    tool_type=ToolType.SHELL
                )
            
            # Execute with timeout
            future = self.executor.submit(self._run_command, command)
            result = future.result(timeout=tool.timeout)
            
            execution_time = time.time() - start_time
            
            if result['returncode'] == 0:
                return ToolResult(
                    success=True,
                    output=result['stdout'],
                    execution_time=execution_time,
                    tool_type=ToolType.SHELL
                )
            else:
                return ToolResult(
                    success=False,
                    output=result['stdout'],
                    error=result['stderr'],
                    execution_time=execution_time,
                    tool_type=ToolType.SHELL
                )
                
        except TimeoutError:
            return ToolResult(
                success=False,
                output="",
                error=f"Command timed out after {tool.timeout} seconds",
                tool_type=ToolType.SHELL
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e),
                tool_type=ToolType.SHELL
            )
    
    def _run_command(self, command: str) -> Dict[str, Any]:
        """Run shell command safely"""
        try:
            args = shlex.split(command)
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=30
            )
            return {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        except Exception as e:
            return {
                'stdout': '',
                'stderr': str(e),
                'returncode': 1
            }
    
    def _is_safe_command(self, command: str) -> bool:
        """Check if command matches safe patterns"""
        if not command.strip():
            return False
            
        # Check against allowed patterns
        for pattern in self.allowed_patterns:
            if re.match(pattern, command):
                return True
        
        return False
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.mcp_manager:
            await self.mcp_manager.disconnect_all()
        
        if self.executor:
            self.executor.shutdown(wait=True)
        
        if self.loop and not self.loop.is_closed():
            self.loop.close()