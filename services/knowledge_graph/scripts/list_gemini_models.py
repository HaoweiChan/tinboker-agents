#!/usr/bin/env python
"""
Utility script to list available Gemini models from Google AI.
Usage: python scripts/list_gemini_models.py
"""

import google.generativeai as genai

from utils.config import get_llm_config


def list_models():
    config = get_llm_config()
    api_key = config.get("google_api_key")
    if not api_key:
        print("No API Key found")
        return

    genai.configure(api_key=api_key)

    print("Listing available models...")
    try:
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods:
                print(f"Name: {m.name}")
                print(f"Display Name: {m.displayName}")
                print(f"Description: {m.description}")
                print("-" * 20)
    except Exception as e:
        print(f"Error listing models: {e}")


if __name__ == "__main__":
    list_models()




