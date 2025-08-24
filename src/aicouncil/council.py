"""
Main Council orchestrator that manages the multi-agent conversation system.
"""
import anthropic
import os
import time
from datetime import datetime
from typing import List
from colorama import Fore, Style

from .agents.definitions import create_agents
from .agents.response_manager import ResponseManager
from .agents.selector import AgentSelector
from .context.manager import ConversationContext
from .models import Message
from .tools.manager import ToolManager
from .ui.display import DisplayManager


class Council:
    """Main orchestrator for the AI Council multi-agent system"""
    
    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.getenv('ANTHROPIC_API_KEY')
        )
        
        # Initialize components
        self.agents = create_agents()
        self.context_manager = ConversationContext()
        self.response_manager = ResponseManager(self.client)
        self.tool_manager = ToolManager()
        self.agent_selector = AgentSelector(self.client, self.agents)
        self.display = DisplayManager()
        
        # Legacy compatibility
        self.conversation_history = []
        self.active_agents = set()

    def run_interactive_session(self):
        """Run the interactive council session"""
        self.display.display_welcome()
        self.display.display_team_members(self.agents)
        
        print(f"\n{Fore.WHITE}Type 'exit' to leave, 'reset' to clear history, or 'help' for commands{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{Style.DIM}Agents can now use real tools for their jobs - try asking about AWS, Kubernetes, APIs, etc.{Style.RESET_ALL}\n")

        while True:
            try:
                user_input = self.display.display_user_input_prompt()

                if user_input.lower() == 'exit':
                    print(f"\n{Fore.WHITE}Council adjourned. Goodbye!{Style.RESET_ALL}")
                    break

                if user_input.lower() == 'reset':
                    self._reset_session()
                    continue

                if user_input.lower() == 'help':
                    self.display.show_help()
                    continue

                if user_input.startswith('@'):
                    self._handle_direct_message(user_input)
                else:
                    self._handle_conversation(user_input)

            except KeyboardInterrupt:
                print(f"\n\n{Fore.WHITE}Council adjourned. Goodbye!{Style.RESET_ALL}")
                break
            except Exception as e:
                print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")

    def _reset_session(self):
        """Reset the conversation state"""
        self.conversation_history = []
        self.active_agents = set()
        self.context_manager = ConversationContext()
        print(f"{Fore.WHITE}Conversation history and context cleared.{Style.RESET_ALL}")

    def _handle_conversation(self, message: str):
        """Handle a normal conversation with automatic agent selection"""
        # Add user message to context
        user_msg = Message(
            content=message,
            sender="User",
            timestamp=datetime.now(),
            tokens=len(message) // 4
        )
        self.context_manager.add_message(user_msg)
        
        # Periodically summarize old messages
        if len(self.context_manager.messages) % 10 == 0:
            self.context_manager.summarize_old_messages(self.client)
        
        # Detect relevant agents
        relevant_agents = self.agent_selector.detect_relevant_agents(message)
        if not relevant_agents:
            relevant_agents = ["saul"]

        self.active_agents = set(relevant_agents)
        responses = self._generate_primary_responses(message, relevant_agents)
        self._handle_interjections(message, relevant_agents, responses)
        self._handle_agent_comments(responses)
        self.display.display_context_status(self.context_manager)

    def _generate_primary_responses(self, message: str, relevant_agents: List[str]) -> List[tuple]:
        """Generate responses from relevant agents"""
        responses = []
        for agent_id in relevant_agents:
            agent = self.agents[agent_id]
            self.display.display_agent_header(agent)

            response_msg = self.response_manager.generate_contextual_response(
                agent=agent,
                message=message,
                context=self.context_manager,
                include_catchphrase=True,
                tool_manager=self.tool_manager
            )
            
            print(response_msg.content)
            print(f"{Style.RESET_ALL}", end="", flush=True)
            
            if not response_msg.is_complete:
                print(f"  {Fore.YELLOW}[Response may be incomplete]{Style.RESET_ALL}")
            
            responses.append((agent_id, response_msg))
            self.context_manager.add_message(response_msg)
            self.conversation_history.append(f"{agent.name}: {response_msg.content}")
            time.sleep(0.5)
        
        return responses

    def _handle_interjections(self, message: str, relevant_agents: List[str], responses: List[tuple]):
        """Handle agent interjections"""
        context_text, _ = self.context_manager.get_context_window()
        
        for agent_id in self.agents:
            if agent_id not in relevant_agents:
                if self.agent_selector.should_agent_interject(agent_id, context_text, self.active_agents):
                    agent = self.agents[agent_id]
                    self.display.display_agent_header(agent, is_interjection=True)

                    interjection_prompt = f"Based on the ongoing discussion about: '{message}'"
                    response_msg = self.response_manager.generate_contextual_response(
                        agent=agent,
                        message=interjection_prompt,
                        context=self.context_manager,
                        include_catchphrase=False,
                        tool_manager=self.tool_manager
                    )
                    
                    print(response_msg.content)
                    print(f"{Style.RESET_ALL}", end="", flush=True)
                    
                    if not response_msg.is_complete:
                        print(f"  {Fore.YELLOW}[Response may be incomplete]{Style.RESET_ALL}")

                    self.active_agents.add(agent_id)
                    self.context_manager.add_message(response_msg)
                    self.conversation_history.append(f"{agent.name}: {response_msg.content}")
                    responses.append((agent_id, response_msg))
                    time.sleep(0.5)

    def _handle_agent_comments(self, responses: List[tuple]):
        """Handle agent-to-agent comments"""
        if len(responses) > 1:
            for i, (agent_id, response_msg) in enumerate(responses):
                for other_id, _ in responses[i + 1:]:
                    from_agent = self.agents[other_id]
                    to_agent = self.agents[agent_id]
                    
                    comment = self.response_manager.agent_to_agent_comment(
                        from_agent, to_agent, response_msg.content
                    )
                    if comment:
                        self.display.display_agent_comment(from_agent, comment)
                        
                        comment_msg = Message(
                            content=comment,
                            sender=from_agent.name,
                            timestamp=datetime.now(),
                            tokens=len(comment) // 4,
                            importance=0.5
                        )
                        self.context_manager.add_message(comment_msg)
                        time.sleep(0.3)

    def _handle_direct_message(self, message: str):
        """Handle direct message to specific agent like @rick or @all"""
        parts = message.split(' ', 1)
        if len(parts) < 2:
            print(f"{Fore.RED}Please include a message after the @mention{Style.RESET_ALL}")
            return

        mention, content = parts
        target = mention[1:].lower()
        
        # Add user message to context
        user_msg = Message(
            content=content,
            sender="User",
            timestamp=datetime.now(),
            tokens=len(content) // 4
        )
        self.context_manager.add_message(user_msg)

        if target == 'all':
            self._message_all_agents(content)
        else:
            self._message_specific_agent(target, content)

    def _message_all_agents(self, content: str):
        """Send message to all agents"""
        for agent_id in self.agents:
            agent = self.agents[agent_id]
            self.display.display_agent_header(agent)
            
            response_msg = self.response_manager.generate_contextual_response(
                agent=agent,
                message=content,
                context=self.context_manager,
                include_catchphrase=True,
                tool_manager=self.tool_manager
            )
            
            print(response_msg.content)
            print(f"{Style.RESET_ALL}", end="", flush=True)
            
            if not response_msg.is_complete:
                print(f"  {Fore.YELLOW}[Response may be incomplete]{Style.RESET_ALL}")
                
            self.context_manager.add_message(response_msg)
            time.sleep(0.5)

    def _message_specific_agent(self, target: str, content: str):
        """Send message to specific agent"""
        agent_id = None
        for aid, agent in self.agents.items():
            if target in agent.name.lower():
                agent_id = aid
                break

        if agent_id:
            agent = self.agents[agent_id]
            self.display.display_agent_header(agent)
            
            response_msg = self.response_manager.generate_contextual_response(
                agent=agent,
                message=content,
                context=self.context_manager,
                include_catchphrase=True,
                tool_manager=self.tool_manager
            )
            
            print(response_msg.content)
            print(f"{Style.RESET_ALL}", end="", flush=True)
            
            if not response_msg.is_complete:
                print(f"  {Fore.YELLOW}[Response may be incomplete]{Style.RESET_ALL}")
                
            self.context_manager.add_message(response_msg)
        else:
            print(f"{Fore.RED}Unknown agent: {target}{Style.RESET_ALL}")