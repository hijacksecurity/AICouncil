#!/usr/bin/env python3
"""
AI Council - Interactive Multi-Agent System with MCP Integration

Main entry point for the AI Council application.
"""

import asyncio
import os
import sys
from colorama import Fore, Style

from .council import Council


async def main():
    """Main entry point with async support for MCP"""
    # Check for API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print(f"{Fore.RED}Error: ANTHROPIC_API_KEY environment variable not set{Style.RESET_ALL}")
        print("Export your key: export ANTHROPIC_API_KEY='your-key-here'")
        sys.exit(1)

    council = Council()
    
    try:
        # Run the interactive session
        council.run_interactive_session()
    except KeyboardInterrupt:
        print(f"\n{Fore.WHITE}Council adjourned. Goodbye!{Style.RESET_ALL}")
    finally:
        # Cleanup MCP connections
        if hasattr(council, 'tool_manager'):
            await council.tool_manager.cleanup()


if __name__ == "__main__":
    # For Python 3.7+ compatibility
    try:
        asyncio.run(main())
    except AttributeError:
        # Fallback for older Python versions
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
        loop.close()