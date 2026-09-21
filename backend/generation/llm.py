import time
import logging
from typing import Optional, Tuple, Dict, Any
from backend.config import get_gemini_api_key, LLM_MODEL
from backend.generation.prompts import SYSTEM_DIRECTIVE

logger = logging.getLogger("generation.llm")

def call_gemini(
    prompt: str,
    system_instruction: str = SYSTEM_DIRECTIVE,
    model_name: str = LLM_MODEL,
    temperature: float = 0.2,
    max_output_tokens: int = 2048
) -> Tuple[Optional[str], float, Optional[Dict[str, int]]]:
    """
    Execute generation via the official google-genai SDK.
    Returns: (generated_text, latency_seconds, token_usage_dict)
    """
    api_key = get_gemini_api_key()
    if not api_key or api_key.startswith("demo_"):
        return None, 0.0, None

    start_time = time.time()
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens
        )

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config
        )

        latency = time.time() - start_time
        token_usage = None
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            token_usage = {
                "prompt_tokens": getattr(response.usage_metadata, "prompt_token_count", 0),
                "candidates_tokens": getattr(response.usage_metadata, "candidates_token_count", 0),
                "total_tokens": getattr(response.usage_metadata, "total_token_count", 0)
            }

        return response.text, latency, token_usage
    except Exception as e:
        latency = time.time() - start_time
        logger.warning(f"Google GenAI LLM call failed for model '{model_name}': {e}")
        return None, latency, None
