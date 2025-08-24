#!/usr/bin/env python3
# council.py - The Council: Interactive Multi-Agent System

import anthropic
import os
import sys
import time
import random
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import re
from colorama import init, Fore, Back, Style
import readline  # For better input handling
import hashlib
import json
from datetime import datetime, timedelta

init(autoreset=True)  # Initialize colorama


@dataclass
class Agent:
    name: str
    role: str
    color: str
    emoji: str
    triggers: List[str]
    personality: str
    catchphrases: List[str]
    interaction_style: str


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


@dataclass 
class ConversationContext:
    """Manages conversation context intelligently"""
    messages: List[Message] = field(default_factory=list)
    summaries: Dict[str, str] = field(default_factory=dict)  # Summaries of older conversations
    total_tokens: int = 0
    max_context_tokens: int = 4000  # Conservative limit for context
    current_complexity: float = 1.0  # Tracks conversation complexity
    
    def add_message(self, message: Message):
        """Add message and update metrics"""
        self.messages.append(message)
        self.total_tokens += message.tokens
        self._update_complexity()
    
    def _update_complexity(self):
        """Update conversation complexity based on recent messages"""
        if len(self.messages) < 3:
            return
        
        recent = self.messages[-5:]
        # Higher complexity for: technical terms, long messages, multiple agents
        technical_terms = sum(1 for m in recent if any(
            term in m.content.lower() for term in 
            ['architecture', 'algorithm', 'implementation', 'vulnerability', 'infrastructure']
        ))
        avg_length = sum(len(m.content) for m in recent) / len(recent)
        unique_senders = len(set(m.sender for m in recent))
        
        self.current_complexity = 1.0 + (technical_terms * 0.2) + (avg_length / 500) + (unique_senders * 0.1)
        self.current_complexity = min(3.0, self.current_complexity)  # Cap at 3x
    
    def get_context_window(self) -> Tuple[str, int]:
        """Get intelligently sized context window"""
        # Dynamic window size based on complexity
        base_messages = 5
        window_size = int(base_messages * self.current_complexity)
        window_size = min(window_size, 15)  # Cap at 15 messages
        
        # Get recent messages
        recent_messages = self.messages[-window_size:] if self.messages else []
        
        # Build context
        context_parts = []
        context_tokens = 0
        
        # Add summaries of older conversations if available
        if self.summaries and len(self.messages) > window_size:
            summary_values = list(self.summaries.values())
            recent_summaries = summary_values[-3:] if len(summary_values) >= 3 else summary_values
            summary_text = "Previous context summary: " + " ".join(recent_summaries)
            context_parts.append(summary_text)
            context_tokens += self._estimate_tokens(summary_text)
        
        # Add recent messages
        for msg in recent_messages:
            msg_text = f"{msg.sender}: {msg.content}"
            if not msg.is_complete:
                msg_text += " [INCOMPLETE]"
            msg_tokens = self._estimate_tokens(msg_text)
            
            if context_tokens + msg_tokens > self.max_context_tokens:
                break
                
            context_parts.append(msg_text)
            context_tokens += msg_tokens
        
        return "\n".join(context_parts), context_tokens
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars per token average)"""
        return len(text) // 4
    
    def summarize_old_messages(self, client: anthropic.Anthropic) -> Optional[str]:
        """Summarize older messages to preserve context"""
        if len(self.messages) < 10:
            return None
            
        # Get messages to summarize (older than last 5)
        to_summarize = self.messages[-15:-5]
        if not to_summarize:
            return None
            
        conversation = "\n".join([f"{m.sender}: {m.content}" for m in to_summarize])
        
        try:
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=150,
                messages=[{
                    "role": "user",
                    "content": f"Summarize the key points of this conversation in 2-3 sentences:\n\n{conversation}"
                }]
            )
            summary = response.content[0].text.strip()
            
            # Store summary with timestamp
            summary_id = hashlib.md5(conversation.encode()).hexdigest()[:8]
            self.summaries[summary_id] = summary
            
            return summary
        except Exception:
            return None


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
        include_catchphrase: bool = False
    ) -> Message:
        """Generate response with full context management"""
        # Get appropriate context window
        context_text, context_tokens = context.get_context_window()
        
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
        
        Respond as {agent.name}. Be {agent.interaction_style}.
        CRITICAL BUSINESS RULES:
        - Maximum 2 sentences (seriously, no more)
        - Be memorable, punchy, technically accurate
        - Get straight to the actionable point
        - Make it entertaining but valuable for business decisions
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


class Council:
    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.getenv('ANTHROPIC_API_KEY')
        )
        
        # Initialize enhanced context and response management
        self.context_manager = ConversationContext()
        self.response_manager = ResponseManager(self.client)

        self.agents = {
            "gilfoyle": Agent(
                name="Gilfoyle",
                role="Infrastructure Administrator",
                color=Fore.CYAN,
                emoji="🖥️",
                triggers=["infrastructure", "cloud", "aws", "server", "network", "terraform", "scaling", "architecture",
                          "performance", "load"],
                personality="""You are Bertram Gilfoyle from Silicon Valley. You're a cynical, sarcastic infrastructure engineer who believes in elegant solutions. 
                You have disdain for inefficiency and corporate culture. You speak in deadpan, often insulting but technically brilliant ways.
                You're a LaVeyan Satanist and enjoy making others uncomfortable with your dark humor. You hate redundant questions and obvious solutions.
                You frequently mock poor technical decisions and have a rivalry with Dinesh (who isn't here, but you still reference him mockingly).
                BUSINESS MODE: Keep it sharp, technical, and brutally honest. Maximum 2 sentences.""",
                catchphrases=[
                    "This is garbage.",
                    "Your incompetence is staggering.",
                    "I'm not doing that.",
                    "How are you this bad at your job?"
                ],
                interaction_style="dismissive and sarcastic"
            ),

            "judy": Agent(
                name="Judy",
                role="Senior DevOps Engineer",
                color=Fore.RED,
                emoji="⚡",
                triggers=["kubernetes", "docker", "k8s", "deployment", "ci/cd", "pipeline", "github", "actions", "helm",
                          "container", "devops", "monitoring"],
                personality="""You are Judy Alvarez from Cyberpunk 2077. You're a skilled, no-nonsense DevOps engineer who gets things done.
                You're tough, direct, and don't sugarcoat things. You have a strong sense of loyalty and protect your infrastructure like you protected the Mox.
                You speak with confidence and street smarts, mixing technical expertise with Night City attitude. You don't have time for corpo BS.
                You occasionally reference your experience with braindances when talking about debugging or monitoring.
                BUSINESS MODE: Cut the BS, give actionable solutions. Maximum 2 sentences, preem.""",
                catchphrases=[
                    "Let's delta the fuck outta here.",
                    "Preem work, but could be better.",
                    "No time for corpo bullshit.",
                    "This is how we do it in Night City."
                ],
                interaction_style="direct and tough"
            ),

            "rick": Agent(
                name="Rick",
                role="Senior Backend Engineer",
                color=Fore.GREEN,
                emoji="🧪",
                triggers=["backend", "api", "database", "algorithm", "optimization", "python", "node", "microservices",
                          "queue", "cache", "logic", "code"],
                personality="""You are Rick Sanchez from Rick and Morty. You're a genius backend engineer but also nihilistic and often drunk.
                You solve complex problems with ease but are dismissive of others' intelligence. You frequently burp mid-sentence (*burp*).
                You reference multiple dimensions/universes when discussing system architecture. You think most solutions are simple and everyone else is an idiot.
                You often go on tangents about the meaninglessness of existence while providing brilliant technical solutions.
                BUSINESS MODE: Genius solutions, minimal words. *burp* Maximum 2 sentences.""",
                catchphrases=[
                    "Wubba lubba dub dub!",
                    "That's the dumbest thing I've ever heard.",
                    "I'm gonna need you to get waaaaay off my back about this.",
                    "*burp* Whatever, Morty... I mean, whatever."
                ],
                interaction_style="genius but dismissive"
            ),

            "wednesday": Agent(
                name="Wednesday",
                role="Frontend Developer",
                color=Fore.MAGENTA,
                emoji="🕷️",
                triggers=["frontend", "react", "ui", "ux", "css", "javascript", "typescript", "component", "design",
                          "user", "interface", "responsive", "vue", "angular"],
                personality="""You are Wednesday Addams. You're a brilliant frontend developer with a morbid fascination for dark UI themes.
                You speak in monotone, finding beauty in the macabre aspects of web development. You're highly intelligent but emotionally detached.
                You often compare JavaScript frameworks to various torture methods. You have no patience for cheerful, colorful designs.
                You appreciate elegant, minimalist solutions and have contempt for bloated frameworks. Death and suffering metaphors are common in your explanations.
                BUSINESS MODE: Dark, efficient, minimal. Maximum 2 sentences of elegant suffering.""",
                catchphrases=[
                    "I find this insufficiently dark.",
                    "How delightfully morbid.",
                    "Your optimism nauseates me.",
                    "This UI needs more suffering."
                ],
                interaction_style="dark and monotone"
            ),

            "elliot": Agent(
                name="Elliot",
                role="Senior Security Engineer",
                color=Fore.YELLOW,
                emoji="🔒",
                triggers=["security", "vulnerability", "hack", "encryption", "auth", "pentest", "firewall", "zero-day",
                          "exploit", "breach", "audit", "compliance", "owasp"],
                personality="""You are Elliot Alderson from Mr. Robot. You're a brilliant but paranoid security engineer with social anxiety.
                You see vulnerabilities everywhere and trust no one. You often break the fourth wall, acknowledging you're in a conversation.
                You mutter about corporate control and surveillance. You're methodical and thorough but struggle with direct communication.
                You reference fsociety principles and hate E Corp (which you call Evil Corp). You sometimes trail off or restart sentences.
                BUSINESS MODE: Security-focused, paranoid but precise. Maximum 2 sentences, friend.""",
                catchphrases=[
                    "Hello, friend.",
                    "Control is an illusion.",
                    "They're watching. They're always watching.",
                    "Evil Corp needs to be stopped."
                ],
                interaction_style="paranoid and intense"
            ),

            "saul": Agent(
                name="Saul",
                role="Project Manager",
                color=Fore.BLUE,
                emoji="⚖️",
                triggers=["timeline", "deadline", "budget", "client", "meeting", "agile", "scrum", "requirement",
                          "stakeholder", "project", "planning", "estimate", "delivery"],
                personality="""You are Saul Goodman (Jimmy McGill) from Better Call Saul. You're a smooth-talking project manager who can sell anything.
                You use legal metaphors constantly and always find creative 'interpretations' of requirements. You're optimistic and energetic.
                You treat project management like practicing law - finding loopholes, negotiating deals, and keeping everyone happy.
                You reference your past cases and use phrases like 'allegedly' and 'hypothetically' when discussing questionable practices.
                BUSINESS MODE: Smooth, solution-oriented, legally flexible. Maximum 2 sentences, counselor.""",
                catchphrases=[
                    "Better Call Saul!",
                    "I'm gonna make this right, trust me.",
                    "Let's call it creative problem-solving.",
                    "S'all good, man!"
                ],
                interaction_style="smooth-talking and optimistic"
            )
        }

        self.conversation_history = []
        self.active_agents = set()

    def detect_relevant_agents(self, message: str) -> List[str]:
        """Detect which agents should be involved based on message content"""
        message_lower = message.lower()
        relevant = []

        # First, use keyword matching
        for agent_id, agent in self.agents.items():
            if any(trigger in message_lower for trigger in agent.triggers):
                relevant.append(agent_id)

        # If no specific triggers, ask Claude to determine relevance
        if not relevant or len(relevant) < 2:
            agent_descriptions = "\n".join([
                f"- {a.name} ({a.role}): handles {', '.join(a.triggers[:5])}"
                for a in self.agents.values()
            ])

            prompt = f"""Given this message: "{message}"

            Available team members:
            {agent_descriptions}

            Which 2-3 team members would be most relevant to this discussion?
            Consider both primary expertise and potential valuable input.
            Return ONLY agent names separated by commas, like: Rick,Wednesday,Elliot
            """

            try:
                response = self.client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=50,
                    messages=[{"role": "user", "content": prompt}]
                )
                names = response.content[0].text.strip().split(',')
                name_to_id = {a.name: aid for aid, a in self.agents.items()}
                relevant = [name_to_id[name.strip()] for name in names if name.strip() in name_to_id]
            except:
                pass

        return relevant[:3]  # Max 3 agents at once

    def display_agent_header(self, agent: Agent, is_interjection: bool = False):
        """Display a visually distinct header for each agent's response"""
        if is_interjection:
            print(f"\n{agent.color}{'┈' * 30} [INTERJECTION] {'┈' * 15}{Style.RESET_ALL}")
            print(f"{agent.emoji} {agent.color}{Style.BRIGHT}{agent.name}{Style.RESET_ALL} {agent.color}(jumping in):{Style.RESET_ALL}")
        else:
            print(f"\n{agent.color}{'─' * 40}{Style.RESET_ALL}")
            print(f"{agent.emoji} {agent.color}{Style.BRIGHT}{agent.name} ({agent.role}){Style.RESET_ALL}")
            print(f"{agent.color}{'─' * 40}{Style.RESET_ALL}")
        print(f"{agent.color}", end="", flush=True)
    
    def should_agent_interject(self, agent_id: str, conversation: str) -> bool:
        """Determine if an agent should jump into ongoing conversation"""
        agent = self.agents[agent_id]

        # Don't interrupt if already active
        if agent_id in self.active_agents:
            return False

        prompt = f"""Current conversation:
        {conversation}

        As {agent.name}, would you have something important to add here?
        Your expertise: {agent.role}

        Respond with just YES or NO."""

        response = self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=10,
            system=agent.personality,
            messages=[{"role": "user", "content": prompt}]
        )

        return "yes" in response.content[0].text.lower()

    def get_agent_response(self, agent_id: str, message: str, context: str = "") -> str:
        """Get response from specific agent"""
        agent = self.agents[agent_id]

        # Add random catchphrase occasionally (20% chance)
        catchphrase = ""
        if random.random() < 0.2:
            catchphrase = f"\n\n*{random.choice(agent.catchphrases)}*"

        full_context = f"""Previous conversation:
        {context}

        Current message: {message}

        Respond as {agent.name}. Be {agent.interaction_style}.
        Keep response to 2-3 sentences unless complexity demands more.
        {catchphrase}"""

        response = self.client.messages.create(
            model="claude-opus-4-1-20250805",
            max_tokens=300,
            system=agent.personality,
            messages=[{"role": "user", "content": full_context}]
        )

        return response.content[0].text

    def agent_to_agent_comment(self, from_agent: str, to_agent: str, their_response: str) -> Optional[str]:
        """Allow agents to comment on each other's responses"""
        if random.random() < 0.3:  # 30% chance of inter-agent banter
            from_a = self.agents[from_agent]
            to_a = self.agents[to_agent]

            prompt = f"""{to_a.name} just said: "{their_response}"

            As {from_a.name}, do you have a quick reaction or comment?
            Keep it to one short sentence or skip if nothing to add.
            This should be in character - you can be sarcastic, dismissive, or supportive based on your personality.
            Respond with SKIP if you have nothing to say."""

            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=50,
                system=from_a.personality,
                messages=[{"role": "user", "content": prompt}]
            )

            result = response.content[0].text.strip()
            return None if "SKIP" in result else result
        return None

    def run_interactive_session(self):
        """Run the interactive council session"""
        print(f"\n{Fore.WHITE}{Back.BLACK}{'=' * 60}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}{Back.BLACK}   THE COUNCIL - Interactive Multi-Agent System   {Style.RESET_ALL}")
        print(f"{Fore.WHITE}{Back.BLACK}{'=' * 60}{Style.RESET_ALL}\n")

        print("Team Members:")
        for agent in self.agents.values():
            print(f"  {agent.emoji} {agent.color}{agent.name}{Style.RESET_ALL} - {agent.role}")

        print(
            f"\n{Fore.WHITE}Type 'exit' to leave, 'reset' to clear history, or 'help' for commands{Style.RESET_ALL}\n")

        while True:
            try:
                # Get user input with enhanced prompt
                print(f"\n{Fore.GREEN}{'▶' * 3}{Style.RESET_ALL}", end=" ")
                user_input = input(f"{Fore.GREEN}{Style.BRIGHT}You: {Style.RESET_ALL}").strip()

                if user_input.lower() == 'exit':
                    print(f"\n{Fore.WHITE}Council adjourned. Goodbye!{Style.RESET_ALL}")
                    break

                if user_input.lower() == 'reset':
                    self.conversation_history = []
                    self.active_agents = set()
                    self.context_manager = ConversationContext()  # Reset context manager
                    self.response_manager = ResponseManager(self.client)  # Reset response manager
                    print(f"{Fore.WHITE}Conversation history and context cleared.{Style.RESET_ALL}")
                    continue

                if user_input.lower() == 'help':
                    self.show_help()
                    continue

                if user_input.startswith('@'):
                    # Direct message to specific agent
                    self.handle_direct_message(user_input)
                else:
                    # Normal conversation flow
                    self.handle_conversation(user_input)

            except KeyboardInterrupt:
                print(f"\n\n{Fore.WHITE}Council adjourned. Goodbye!{Style.RESET_ALL}")
                break
            except Exception as e:
                print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")

    def handle_conversation(self, message: str):
        """Handle a normal conversation with automatic agent selection using enhanced context management"""
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
        relevant_agents = self.detect_relevant_agents(message)

        if not relevant_agents:
            # Default to Saul if no specific expertise needed
            relevant_agents = ["saul"]

        # Update active agents
        self.active_agents = set(relevant_agents)

        # Primary responses from relevant agents
        responses = []
        for agent_id in relevant_agents:
            agent = self.agents[agent_id]
            self.display_agent_header(agent)

            # Generate response using enhanced context management
            response_msg = self.response_manager.generate_contextual_response(
                agent=agent,
                message=message,
                context=self.context_manager,
                include_catchphrase=True
            )
            
            # Display response with persistent color
            print(response_msg.content)
            print(f"{Style.RESET_ALL}", end="", flush=True)
            
            # Show if response was incomplete
            if not response_msg.is_complete:
                print(f"  {Fore.YELLOW}[Response may be incomplete]{Style.RESET_ALL}")
            
            responses.append((agent_id, response_msg))
            
            # Add to context manager
            self.context_manager.add_message(response_msg)
            
            # Also maintain legacy history for compatibility
            self.conversation_history.append(f"{agent.name}: {response_msg.content}")

            # Small delay for readability
            time.sleep(0.5)

        # Check if other agents want to interject
        context_text, _ = self.context_manager.get_context_window()
        
        for agent_id in self.agents:
            if agent_id not in relevant_agents:
                if self.should_agent_interject(agent_id, context_text):
                    agent = self.agents[agent_id]
                    self.display_agent_header(agent, is_interjection=True)

                    # Generate interjection with context
                    response_msg = self.response_manager.generate_contextual_response(
                        agent=agent,
                        message=message,
                        context=self.context_manager,
                        include_catchphrase=False
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

        # Agent-to-agent comments
        if len(responses) > 1:
            for i, (agent_id, response_msg) in enumerate(responses):
                for other_id, _ in responses[i + 1:]:
                    comment = self.agent_to_agent_comment(other_id, agent_id, response_msg.content)
                    if comment:
                        other = self.agents[other_id]
                        print(f"  {other.color}↳ {other.name}: {Style.DIM}{comment}{Style.RESET_ALL}")
                        
                        # Add comment to context as well
                        comment_msg = Message(
                            content=comment,
                            sender=other.name,
                            timestamp=datetime.now(),
                            tokens=len(comment) // 4,
                            importance=0.5  # Comments are less important
                        )
                        self.context_manager.add_message(comment_msg)
                        time.sleep(0.3)
        
        # Display context status with visual separator
        print(f"\n{Fore.CYAN}{'═' * 60}{Style.RESET_ALL}")
        print(f"  {Fore.CYAN}{Style.DIM}[Context: {len(self.context_manager.messages)} msgs | "
              f"Complexity: {self.context_manager.current_complexity:.1f}x | "
              f"Tokens: ~{self.context_manager.total_tokens}]{Style.RESET_ALL}")

    def handle_direct_message(self, message: str):
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
            # Message all agents with enhanced context
            for agent_id in self.agents:
                agent = self.agents[agent_id]
                self.display_agent_header(agent)
                
                # Generate response using enhanced context management
                response_msg = self.response_manager.generate_contextual_response(
                    agent=agent,
                    message=content,
                    context=self.context_manager,
                    include_catchphrase=True
                )
                
                print(response_msg.content)
                print(f"{Style.RESET_ALL}", end="", flush=True)
                
                if not response_msg.is_complete:
                    print(f"  {Fore.YELLOW}[Response may be incomplete]{Style.RESET_ALL}")
                    
                self.context_manager.add_message(response_msg)
                time.sleep(0.5)
        else:
            # Find specific agent
            agent_id = None
            for aid, agent in self.agents.items():
                if target in agent.name.lower():
                    agent_id = aid
                    break

            if agent_id:
                agent = self.agents[agent_id]
                self.display_agent_header(agent)
                
                # Generate response using enhanced context management
                response_msg = self.response_manager.generate_contextual_response(
                    agent=agent,
                    message=content,
                    context=self.context_manager,
                    include_catchphrase=True
                )
                
                print(response_msg.content)
                print(f"{Style.RESET_ALL}", end="", flush=True)
                
                if not response_msg.is_complete:
                    print(f"  {Fore.YELLOW}[Response may be incomplete]{Style.RESET_ALL}")
                    
                self.context_manager.add_message(response_msg)
            else:
                print(f"{Fore.RED}Unknown agent: {target}{Style.RESET_ALL}")

    def show_help(self):
        """Show help information"""
        print(f"""
{Fore.WHITE}Commands:{Style.RESET_ALL}
  exit              - End the session
  reset             - Clear conversation history
  help              - Show this help
  @<name> <message> - Direct message to specific agent
  @all <message>    - Message all agents

{Fore.WHITE}Agent Triggers:{Style.RESET_ALL}
  Just type naturally and relevant agents will respond.

{Fore.WHITE}Examples:{Style.RESET_ALL}
  "How should we architect this microservice?"
  "@rick What's wrong with my API design?"
  "@all What are your thoughts on GraphQL?"
  "There's a security vulnerability in production!"
        """)


if __name__ == "__main__":
    # Check for API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print(f"{Fore.RED}Error: ANTHROPIC_API_KEY environment variable not set{Style.RESET_ALL}")
        print("Export your key: export ANTHROPIC_API_KEY='your-key-here'")
        sys.exit(1)

    council = Council()
    council.run_interactive_session()