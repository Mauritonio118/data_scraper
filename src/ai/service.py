from typing import Optional
import os
from .providers.base import AIProvider
from .providers.gemini import GeminiProvider

class AIService:
    """
    Service layer for interacting with AI models.
    Acts as a factory and facade for different AI providers.
    """
    
    def __init__(self, provider: str = "google", **kwargs):
        """
        Initialize the AI Service.
        
        Args:
            provider (str): The name of the provider to use ('google', 'ollama', etc.). Defaults to 'google'.
            **kwargs: Arguments passed to the provider's constructor (e.g., model_name, api_key).
        """
        self.provider_name = provider.lower()
        self.provider_instance: AIProvider = self._factory(self.provider_name, **kwargs)

    def _factory(self, provider_name: str, **kwargs) -> AIProvider:
        """
        Factory method to instantiate the correct provider.
        """
        if provider_name == "google" or provider_name == "gemini":
            return GeminiProvider(**kwargs)
        # Future implementations:
        # elif provider_name == "ollama":
        #     return OllamaProvider(**kwargs)
        # elif provider_name == "openai":
        #     return OpenAIProvider(**kwargs)
        else:
            raise ValueError(f"Unsupported AI provider: {provider_name}")

    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate content using the configured provider.
        
        Args:
            prompt (str): The prompt to send to the AI.
            **kwargs: Additional arguments for the generation (e.g. temperature).
        
        Returns:
            str: The AI's response.
        """
        return self.provider_instance.generate_content(prompt, **kwargs)
