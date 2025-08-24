"""
MCP (Model Context Protocol) server integration for advanced agent capabilities.
"""
import asyncio
import json
import subprocess
import time
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

from ..models import MCPTool, ToolResult, ToolType


class MCPServerConfig:
    """Configuration for MCP servers"""
    
    # MCP server configurations for each agent
    SERVERS = {
        "gilfoyle_aws": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-aws"],
            "env": {"AWS_PROFILE": "default"},
            "description": "AWS infrastructure management"
        },
        "judy_k8s": {
            "command": "docker",
            "args": ["run", "--rm", "-i", "mcp-k8s-server"],
            "env": {"KUBECONFIG": "/root/.kube/config"},
            "description": "Kubernetes cluster management"
        },
        "rick_dev": {
            "command": "python",
            "args": ["-m", "mcp_dev_server"],
            "env": {},
            "description": "Development and API testing tools"
        },
        "wednesday_web": {
            "command": "node",
            "args": ["web-security-mcp-server.js"],
            "env": {},
            "description": "Web security and accessibility testing"
        },
        "elliot_security": {
            "command": "python",
            "args": ["-m", "security_mcp_server"],
            "env": {},
            "description": "Security scanning and penetration testing"
        }
    }


class MCPClient:
    """Client for communicating with MCP servers"""
    
    def __init__(self, server_name: str, config: Dict[str, Any]):
        self.server_name = server_name
        self.config = config
        self.process = None
        self.available_tools = {}
        
    async def connect(self) -> bool:
        """Connect to the MCP server"""
        try:
            # Start the MCP server process
            env = {**self.config.get("env", {})}
            self.process = await asyncio.create_subprocess_exec(
                self.config["command"],
                *self.config["args"],
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            # Initialize MCP protocol
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "aicouncil",
                        "version": "1.0.0"
                    }
                }
            }
            
            await self._send_request(init_request)
            response = await self._read_response()
            
            if response and "result" in response:
                # Get available tools
                await self._list_tools()
                return True
                
            return False
            
        except Exception as e:
            print(f"Failed to connect to MCP server {self.server_name}: {e}")
            return False
    
    async def _send_request(self, request: Dict[str, Any]):
        """Send JSON-RPC request to MCP server"""
        if self.process and self.process.stdin:
            request_str = json.dumps(request) + "\n"
            self.process.stdin.write(request_str.encode())
            await self.process.stdin.drain()
    
    async def _read_response(self) -> Optional[Dict[str, Any]]:
        """Read JSON-RPC response from MCP server"""
        if self.process and self.process.stdout:
            try:
                line = await asyncio.wait_for(self.process.stdout.readline(), timeout=5.0)
                if line:
                    return json.loads(line.decode().strip())
            except (asyncio.TimeoutError, json.JSONDecodeError) as e:
                print(f"Error reading response from {self.server_name}: {e}")
        return None
    
    async def _list_tools(self):
        """List available tools from the MCP server"""
        list_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        await self._send_request(list_request)
        response = await self._read_response()
        
        if response and "result" in response and "tools" in response["result"]:
            for tool in response["result"]["tools"]:
                self.available_tools[tool["name"]] = tool
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool on the MCP server"""
        if tool_name not in self.available_tools:
            raise ValueError(f"Tool {tool_name} not available on server {self.server_name}")
        
        call_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        await self._send_request(call_request)
        response = await self._read_response()
        
        if response and "result" in response:
            return response["result"]
        elif response and "error" in response:
            raise RuntimeError(f"MCP tool error: {response['error']}")
        else:
            raise RuntimeError("No response from MCP server")
    
    async def disconnect(self):
        """Disconnect from the MCP server"""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            self.process = None


class MCPToolManager:
    """Enhanced tool manager with MCP server support"""
    
    def __init__(self):
        self.mcp_clients: Dict[str, MCPClient] = {}
        self.connected_servers = set()
        
    async def ensure_server_connection(self, server_name: str) -> bool:
        """Ensure MCP server is connected"""
        if server_name in self.connected_servers:
            return True
            
        if server_name not in MCPServerConfig.SERVERS:
            return False
            
        config = MCPServerConfig.SERVERS[server_name]
        client = MCPClient(server_name, config)
        
        if await client.connect():
            self.mcp_clients[server_name] = client
            self.connected_servers.add(server_name)
            return True
        
        return False
    
    async def execute_mcp_tool(self, tool: MCPTool, args: Dict[str, str]) -> ToolResult:
        """Execute an MCP tool"""
        start_time = time.time()
        
        try:
            # Ensure server is connected
            if not await self.ensure_server_connection(tool.server_name):
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Failed to connect to MCP server: {tool.server_name}",
                    tool_type=ToolType.MCP
                )
            
            # Get the client and execute the tool
            client = self.mcp_clients[tool.server_name]
            result = await client.call_tool(tool.name, args)
            
            execution_time = time.time() - start_time
            
            # Format the response for display
            if isinstance(result, dict):
                if "content" in result:
                    # MCP content response
                    output = self._format_mcp_content(result["content"])
                    return ToolResult(
                        success=True,
                        output=output,
                        execution_time=execution_time,
                        tool_type=ToolType.MCP,
                        raw_data=result
                    )
                else:
                    # Direct response
                    output = json.dumps(result, indent=2)
                    return ToolResult(
                        success=True,
                        output=output,
                        execution_time=execution_time,
                        tool_type=ToolType.MCP,
                        raw_data=result
                    )
            else:
                return ToolResult(
                    success=True,
                    output=str(result),
                    execution_time=execution_time,
                    tool_type=ToolType.MCP
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            return ToolResult(
                success=False,
                output="",
                error=str(e),
                execution_time=execution_time,
                tool_type=ToolType.MCP
            )
    
    def _format_mcp_content(self, content: List[Dict[str, Any]]) -> str:
        """Format MCP content response for display"""
        formatted_parts = []
        
        for item in content:
            if item.get("type") == "text":
                formatted_parts.append(item.get("text", ""))
            elif item.get("type") == "resource":
                formatted_parts.append(f"Resource: {item.get('resource', {}).get('uri', 'Unknown')}")
            else:
                formatted_parts.append(json.dumps(item, indent=2))
        
        return "\n".join(formatted_parts)
    
    async def disconnect_all(self):
        """Disconnect from all MCP servers"""
        for client in self.mcp_clients.values():
            await client.disconnect()
        
        self.mcp_clients.clear()
        self.connected_servers.clear()