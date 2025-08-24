"""
AI Council - Interactive Multi-Agent System

A sophisticated multi-agent conversation system featuring 6 AI personalities
with distinct expertise areas, real tool capabilities, and natural conversation flow.
"""

__version__ = "1.0.0"
__author__ = "AI Council Team"

from .council import Council
from .models import Agent, Tool, ToolResult, Message

__all__ = ["Council", "Agent", "Tool", "ToolResult", "Message"]