import os
from .base import AIProvider
from typing import Optional
from google import genai
from google.genai import types

class GeminiProvider(AIProvider):
    """
    Implementation of AIProvider for Google's Gemini models using the new google-genai SDK.
    """
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.0-flash-lite"):
        """
        Initialize the Gemini provider.
        
        Args:
            api_key (Optional[str]): Google API key. If None, it tries to fetch 'GOOGLE_API_KEY' from env.
            model_name (str): The name of the Gemini model to use. Defaults to "gemini-2.0-flash-lite".
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY is not set. Please set it in your environment variables or pass it to the constructor.")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name

    def generate_content(self, prompt: str, **kwargs) -> str:
        """
        Generates content using the Google Gemini model.
        
        Args:
            prompt (str): The input prompt.
            **kwargs: Additional generation configuration (temperature, top_p, top_k, max_output_tokens, etc.).
            
        Returns:
            str: The generated text.
        """
        # Map common kwargs to Gemini's expected config
        # The new SDK uses 'config' parameter with types.GenerateContentConfig
        
        config_args = {}
        
        # Mapping known keys to the new config structure if needed.
        # Common ones like temperature, top_p, top_k, max_output_tokens, stop_sequences usually work.
        valid_keys = ['temperature', 'top_p', 'top_k', 'max_output_tokens', 'stop_sequences']
        
        for key in valid_keys:
            if key in kwargs:
                config_args[key] = kwargs[key]

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(**config_args) if config_args else None
            )
            return response.text
        except Exception as e:
            # Handle API errors 
            raise RuntimeError(f"Error generating content with Gemini: {e}")
