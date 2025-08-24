"""
Response generation and management system.
"""
import anthropic
import random
import re
from datetime import datetime
from typing import Dict, Optional, Tuple

from ..context.manager import ConversationContext
from ..models import Agent, Message
from ..tools.manager import ToolManager


class ResponseManager:
    """Manages response generation with completion verification and continuation"""
    
    def __init__(self, client: anthropic.Anthropic):
        self.client = client
        self.max_response_tokens = 400  # Reduced for concise business responses
        self.continuation_threshold = 0.9  # If response uses >90% of tokens, might need continuation
        
    def get_complete_response(
        self, 
        agent: Agent,
        prompt: str,
        max_attempts: int = 3
    ) -> Tuple[str, bool, int]:
        """
        Get a complete response, continuing if necessary
        Returns: (response_text, is_complete, total_tokens)
        """
        full_response = []
        total_tokens = 0
        is_complete = False
        attempt = 0
        continuation_prompt = prompt
        
        while attempt < max_attempts and not is_complete:
            try:
                response = self.client.messages.create(
                    model="claude-opus-4-1-20250805",
                    max_tokens=self.max_response_tokens,
                    system=agent.personality,
                    messages=[{"role": "user", "content": continuation_prompt}]
                )
                
                response_text = response.content[0].text
                response_tokens = len(response_text) // 4  # Rough estimate
                total_tokens += response_tokens
                
                # Check if response appears complete
                is_complete = self._verify_completion(response_text, response_tokens)
                
                full_response.append(response_text)
                
                if not is_complete:
                    # Prepare continuation prompt
                    continuation_prompt = f"""Continue your previous response. You were saying:
                    "{response_text[-100:]}"
                    
                    Please continue from where you left off."""
                    attempt += 1
                else:
                    break
                    
            except Exception as e:
                from colorama import Fore, Style
                print(f"{Fore.YELLOW}Warning: Response generation error: {e}{Style.RESET_ALL}")
                is_complete = True  # Stop trying
                
        combined_response = " ".join(full_response)
        return combined_response, is_complete, total_tokens
    
    def _verify_completion(self, response: str, tokens_used: int) -> bool:
        """Verify if a response appears complete"""
        # Check if response used most of available tokens
        if tokens_used > self.max_response_tokens * self.continuation_threshold:
            # Check for incomplete sentences
            if response and not response.rstrip().endswith(('.', '!', '?', '"', ')')):
                return False
                
        # Check for obvious cutoffs
        cutoff_indicators = [
            'Additionally,', 'Furthermore,', 'However,', 'Also,',
            'First,', 'Second,', 'Third,', 'Finally,'
        ]
        
        last_words = response.split()[-3:] if response else []
        for indicator in cutoff_indicators:
            if indicator in ' '.join(last_words):
                return False
                
        return True
    
    def generate_contextual_response(
        self,
        agent: Agent,
        message: str,
        context: ConversationContext,
        include_catchphrase: bool = False,
        tool_manager: Optional[ToolManager] = None,
        minimal_context: bool = False
    ) -> Message:
        """Generate response with full context management and optional tool use"""
        if minimal_context:
            # For direct messages, use minimal context to avoid "duplicate question" issues
            context_text = f"User: {message}"
            context_tokens = len(context_text) // 4
        else:
            # Get appropriate context window, excluding this agent's own responses to avoid "same question" issue
            context_text, context_tokens = context.get_context_window(exclude_agent=agent.name)
        
        # Check if agent should use tools
        tool_output = ""
        if tool_manager and agent.tools:
            tool_output = self._maybe_use_tools(agent, message, context_text, tool_manager)
        
        # Add catchphrase if needed
        catchphrase = ""
        if include_catchphrase and random.random() < 0.2:
            catchphrase = f"\n\n*{random.choice(agent.catchphrases)}*"
        
        # Build prompt with dynamic context
        prompt = f"""Previous conversation:
        {context_text}
        
        Current message: {message}
        
        Context tokens used: {context_tokens}/{context.max_context_tokens}
        Conversation complexity: {context.current_complexity:.1f}x
        
        {tool_output}
        
        Respond as {agent.name}. Be {agent.interaction_style}.
        CRITICAL BUSINESS RULES:
        - Maximum 2 sentences (seriously, no more)
        - Be memorable, punchy, technically accurate
        - Get straight to the actionable point
        - Make it entertaining but valuable for business decisions
        - If you used tools, incorporate the results naturally into your response
        - Remember: The user is your boss - show appropriate respect while staying true to your character
        - You can reference your colleagues by name (Gilfoyle, Judy, Rick, Wednesday, Elliot, Saul) and their opinions
        {catchphrase}"""
        
        # Get complete response
        response_text, is_complete, tokens_used = self.get_complete_response(agent, prompt)
        
        # Create message object
        return Message(
            content=response_text,
            sender=agent.name,
            timestamp=datetime.now(),
            tokens=tokens_used,
            importance=context.current_complexity,
            is_complete=is_complete
        )
    
    def _maybe_use_tools(self, agent: Agent, message: str, context: str, tool_manager: ToolManager) -> str:
        """Determine if agent should use tools and execute them"""
        if not agent.tools:
            return ""
        
        # Simple heuristic: use tools if message contains relevant keywords
        message_lower = message.lower() + " " + context.lower()
        
        tool_triggers = {
            'aws_status': ['aws', 'account', 'credentials', 'access'],
            'aws_regions': ['regions', 'availability', 'zones'],
            'kubectl_status': ['cluster', 'kubernetes', 'k8s'],
            'kubectl_pods': ['pods', 'containers', 'running'],
            'kubectl_nodes': ['nodes', 'workers'],
            'api_test': ['api', 'endpoint', 'url', 'http'],
            'dns_lookup': ['dns', 'domain', 'lookup'],
            'port_check': ['port', 'connection', 'tcp'],
            'web_check': ['website', 'web', 'headers'],
            'security_headers': ['security', 'headers', 'https'],
            'dns_enum': ['enumerate', 'recon', 'scan']
        }
        
        tools_to_run = []
        for tool in agent.tools:
            if tool.name in tool_triggers:
                if any(trigger in message_lower for trigger in tool_triggers[tool.name]):
                    tools_to_run.append(tool)
        
        if not tools_to_run:
            return ""
        
        # Execute tools and format results
        tool_results = []
        for tool in tools_to_run[:2]:  # Max 2 tools per response
            # Extract arguments from message (simple implementation)
            args = self._extract_tool_args(tool, message)
            result = tool_manager.execute_tool(tool, args)
            
            if result.success:
                tool_results.append(f"Tool '{tool.name}' output:\n{result.output[:500]}")  # Limit output
            else:
                tool_results.append(f"Tool '{tool.name}' failed: {result.error}")
        
        if tool_results:
            return f"TOOL EXECUTION RESULTS (incorporate these into your response):\n" + "\n\n".join(tool_results) + "\n\n"
        
        return ""
    
    def _extract_tool_args(self, tool, message: str) -> Dict[str, str]:
        """Extract arguments for tool from message (basic implementation)"""
        args = {}
        
        # Simple URL extraction
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, message)
        if urls and '{url}' in tool.command_template:
            args['url'] = urls[0]
        
        # Simple domain extraction
        domain_pattern = r'(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}'
        domains = re.findall(domain_pattern, message.replace('http://', '').replace('https://', ''))
        if domains and '{domain}' in tool.command_template:
            args['domain'] = domains[0]
        
        # Simple host:port extraction
        host_port_pattern = r'([a-zA-Z0-9.-]+):(\d+)'
        host_ports = re.findall(host_port_pattern, message)
        if host_ports and '{host}' in tool.command_template:
            args['host'] = host_ports[0][0]
            args['port'] = host_ports[0][1]
        
        return args
    
    def agent_to_agent_comment(self, from_agent: Agent, to_agent: Agent, their_response: str) -> Optional[str]:
        """Allow agents to comment on each other's responses"""
        if random.random() < 0.4:  # 40% chance for team interaction
            prompt = f"""{to_agent.name} just said: "{their_response}"

            As {from_agent.name}, do you have a quick reaction or comment to your colleague {to_agent.name}?
            Remember: you can be your COMPLETE unfiltered self with your teammates - no workplace politeness needed here.
            Be sarcastic, supportive, dismissive, or whatever fits your personality.
            Reference shared experiences, mock each other, build on their ideas, or call them out.
            Feel free to mention other teammates by name if relevant.
            Keep it to one punchy sentence or respond with SKIP if nothing to add."""

            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=60,
                system=from_agent.personality,
                messages=[{"role": "user", "content": prompt}]
            )

            result = response.content[0].text.strip()
            return None if "SKIP" in result else result
        return None