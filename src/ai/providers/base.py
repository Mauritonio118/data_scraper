from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class AIProvider(ABC):
    """
    Abstract base class for AI providers.
    Defines the standard interface that all AI providers must implement.
    """

    @abstractmethod
    def generate_content(self, prompt: str, **kwargs) -> str:
        """
        Generates text content based on the given prompt.
        
        Args:
            prompt (str): The input prompt for the AI.
            **kwargs: Additional arguments specific to the provider (e.g., max_tokens, temperature).
            
        Returns:
            str: The generated text response.
        """
        pass
