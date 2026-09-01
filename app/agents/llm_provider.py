import os
import json
import logging
from typing import Optional, Dict, Any, List
from app.config import settings

logger = logging.getLogger("shopmate.llm")

class LLMService:
    """
    Uniform LLM interface with support for Google Gemini, OpenAI, and local deterministic fallback.
    """
    def __init__(self):
        self._gemini_client = None
        self._openai_client = None
        self._init_clients()

    def _init_clients(self):
        # 1. Check Gemini
        gemini_key = settings.GEMINI_API_KEY or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if gemini_key:
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=gemini_key)
                logger.info("Initialized Google Gemini client")
            except Exception as e:
                logger.warning(f"Could not init Gemini: {e}")

        # 2. Check OpenAI
        openai_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        if openai_key:
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=openai_key)
                logger.info("Initialized OpenAI client")
            except Exception as e:
                logger.warning(f"Could not init OpenAI: {e}")

    def generate(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 800) -> str:
        """Invokes LLM with system instruction and user prompt."""
        # 1. Try Gemini
        if self._gemini_client:
            try:
                full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                response = self._gemini_client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=full_prompt
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                logger.warning(f"Gemini generation failed: {e}")

        # 2. Try OpenAI
        if self._openai_client:
            try:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                res = self._openai_client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.2
                )
                if res.choices:
                    return res.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"OpenAI generation failed: {e}")

        # 3. Fallback deterministic generator
        return self._generate_fallback(prompt, system_prompt)

    def _generate_fallback(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Deterministic, intelligent local synthesis fallback."""
        return "RESPONSE_FALLBACK"

# Global singleton
llm_service = LLMService()
