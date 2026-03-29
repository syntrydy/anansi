"""
LLM infrastructure.
Provides factory for Text LLM clients (Anthropic or Ollama).
"""

def get_llm() -> None:
    """
    Factory function returning the appropriate LLM based on environment (cloud vs local).
    """
    # TODO: Implement dynamic instantiation of ChatAnthropic or ChatOllama.
    pass
