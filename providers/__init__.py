"""
AutoGen Council Provider System
===============================

Modular LLM provider system with automatic fallback support.
"""

class CloudRetry(Exception):
    """Exception to trigger fallback to next provider"""
    def __init__(self, reason: str, provider: str = "", response_text: str = ""):
        self.reason = reason
        self.provider = provider
        self.response_text = response_text
        super().__init__(f"CloudRetry: {reason}")

from . import mistral_llm, openai_llm

__all__ = ["CloudRetry", "mistral_llm", "openai_llm"] 