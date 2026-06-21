#!/usr/bin/env python3
"""
Configuration module for AI Business Automator
Loads OpenRouter API key from ~/.hermes/.env
"""

import os
from pathlib import Path
from dotenv import load_dotenv


def load_config():
    """
    Load configuration from ~/.hermes/.env
    
    Returns:
        dict: Configuration dictionary with API keys
        
    Raises:
        RuntimeError: If OPENROUTER_API_KEY is not found
    """
    # Load environment variables from ~/.hermes/.env
    hermes_env = Path.home() / ".hermes" / ".env"
    
    if hermes_env.exists():
        load_dotenv(hermes_env)
        print(f"✓ Loaded config from {hermes_env}")
    else:
        print(f"⚠ Warning: {hermes_env} not found")
    
    # Get OpenRouter API key
    api_key = os.getenv('OPENROUTER_API_KEY')
    
    if not api_key:
        raise RuntimeError(
            f"OPENROUTER_API_KEY not found!\n"
            f"Please add it to {hermes_env}\n"
            f"Format: OPENROUTER_API_KEY=your_key_here"
        )
    
    return {
        'openrouter_api_key': api_key,
        'openrouter_url': 'https://openrouter.ai/api/v1/chat/completions'
    }


# Load config at module import
try:
    CONFIG = load_config()
except RuntimeError as e:
    print(f"❌ Configuration Error: {e}")
    CONFIG = None
