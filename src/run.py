#!/usr/bin/env python3
"""
AI Council Entry Point

Clean entry point for the AI Council application.
All source code is properly organized in the src/ folder.
"""

import sys
import os

# Add current directory to Python path for local imports
sys.path.insert(0, os.path.dirname(__file__))

# Import and run the main function
from aicouncil.main import main
import asyncio

if __name__ == "__main__":
    # For Python 3.7+ compatibility
    try:
        asyncio.run(main())
    except AttributeError:
        # Fallback for older Python versions
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
        loop.close()