"""
Conversation context management system.
"""
import anthropic
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ..models import Message


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
    
    def get_context_window(self, exclude_agent: Optional[str] = None) -> Tuple[str, int]:
        """Get intelligently sized context window, optionally excluding specific agent's responses"""
        # Dynamic window size based on complexity
        base_messages = 5
        window_size = int(base_messages * self.current_complexity)
        window_size = min(window_size, 15)  # Cap at 15 messages
        
        # Get recent messages
        recent_messages = self.messages[-window_size:] if self.messages else []
        
        # Filter out excluded agent's responses if specified
        if exclude_agent:
            recent_messages = [msg for msg in recent_messages if msg.sender != exclude_agent]
        
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