"""
UI display utilities for the AI Council.
"""
from colorama import Fore, Back, Style

from ..models import Agent


class DisplayManager:
    """Handles all visual display formatting for the AI Council"""
    
    @staticmethod
    def display_agent_header(agent: Agent, is_interjection: bool = False):
        """Display a visually distinct header for each agent's response"""
        if is_interjection:
            print(f"\n{agent.color}{'┈' * 30} [INTERJECTION] {'┈' * 15}{Style.RESET_ALL}")
            print(f"{agent.emoji} {agent.color}{Style.BRIGHT}{agent.name}{Style.RESET_ALL} {agent.color}(jumping in):{Style.RESET_ALL}")
        else:
            print(f"\n{agent.color}{'─' * 40}{Style.RESET_ALL}")
            print(f"{agent.emoji} {agent.color}{Style.BRIGHT}{agent.name} ({agent.role}){Style.RESET_ALL}")
            print(f"{agent.color}{'─' * 40}{Style.RESET_ALL}")
        print(f"{agent.color}", end="", flush=True)
    
    @staticmethod
    def display_welcome():
        """Display welcome banner"""
        print(f"\n{Fore.WHITE}{Back.BLACK}{'=' * 60}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}{Back.BLACK}   THE COUNCIL - Interactive Multi-Agent System   {Style.RESET_ALL}")
        print(f"{Fore.WHITE}{Back.BLACK}{'=' * 60}{Style.RESET_ALL}\n")
    
    @staticmethod
    def display_team_members(agents: dict):
        """Display team member list"""
        print("Team Members:")
        for agent in agents.values():
            tools_str = f" ({len(agent.tools)} tools)" if agent.tools else ""
            print(f"  {agent.emoji} {agent.color}{agent.name}{Style.RESET_ALL} - {agent.role}{tools_str}")
    
    @staticmethod
    def display_context_status(context_manager):
        """Display context status with visual separator"""
        print(f"\n{Fore.CYAN}{'═' * 60}{Style.RESET_ALL}")
        print(f"  {Fore.CYAN}{Style.DIM}[Context: {len(context_manager.messages)} msgs | "
              f"Complexity: {context_manager.current_complexity:.1f}x | "
              f"Tokens: ~{context_manager.total_tokens}]{Style.RESET_ALL}")
    
    @staticmethod
    def display_user_input_prompt():
        """Display user input prompt"""
        print(f"\n{Fore.GREEN}{'▶' * 3}{Style.RESET_ALL}", end=" ")
        return input(f"{Fore.GREEN}{Style.BRIGHT}You: {Style.RESET_ALL}").strip()
    
    @staticmethod
    def display_agent_comment(agent: Agent, comment: str):
        """Display agent-to-agent comment"""
        print(f"  {agent.color}↳ {agent.name}: {Style.DIM}{comment}{Style.RESET_ALL}")
    
    @staticmethod
    def show_help():
        """Show help information"""
        print(f"""
{Fore.WHITE}Commands:{Style.RESET_ALL}
  exit              - End the session
  reset             - Clear conversation history
  help              - Show this help
  @<name> <message> - Direct message to specific agent
  @all <message>    - Message all agents

{Fore.WHITE}New Features:{Style.RESET_ALL}
  • Natural 1-3 agent selection (no more forced 2-3 responses)
  • Smart interjections based on expertise relevance
  • Real tool integration - agents can now run commands!
  • Enhanced context management with conversation complexity

{Fore.WHITE}Agent Tools:{Style.RESET_ALL}
  🖥️  Gilfoyle  - AWS CLI commands (status, regions)
  ⚡  Judy     - Kubernetes commands (pods, nodes, cluster-info)  
  🧪  Rick     - API testing, DNS lookup, port checking
  🕷️  Wednesday - Website header checking
  🔒  Elliot   - Security headers, DNS enumeration
  ⚖️  Saul     - Pure charm (no tools needed)

{Fore.WHITE}Examples (with tools):{Style.RESET_ALL}
  "Check AWS account status"        → Gilfoyle runs aws sts get-caller-identity
  "What pods are running?"          → Judy runs kubectl get pods
  "Test https://example.com"        → Rick/Wednesday check the API
  "Check security headers for site.com" → Elliot investigates
  "How should we scale this?"       → Natural selection picks relevant experts
        """)