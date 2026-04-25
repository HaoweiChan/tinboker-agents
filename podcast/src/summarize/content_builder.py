"""
Workflow API Integration

Handles integration with the Workflow API for transcript analysis.
"""

import os
import requests
from typing import Optional


def is_workflow_api_available() -> bool:
    """Check if Workflow API is available (has API key)."""
    return os.getenv("DIFI_API_KEY") is not None


def analyze_transcript_with_workflow_api(
    transcript: str,
    source: str = "Podcast",
    episode_title: str = "Episode",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    user_id: Optional[str] = None,
    timeout: int = 300,
    words: Optional[list] = None,
    sentences: Optional[list] = None
) -> str:
    """
    Analyze transcript using Workflow API (Blocking Mode - Recommended).
    
    This method calls the Workflow API endpoint to generate a markdown report
    from the transcript. The output follows content guidelines:
    - Language: Traditional Chinese (繁體中文)
    - Stock Tickers: [Display Name](#ticker:SYMBOL)
    - Tags: [Tag Name](#tag:TAG_NAME)
    - Structure: H1 title, H2 sections, H3 subsections
    - Content: Financial/market focus only
    
    Args:
        transcript: Transcript text content
        source: Name of the podcast/source
        episode_title: Title of the episode
        api_key: DIFI API key. If None, will try to load from DIFI_API_KEY env var.
        base_url: Base URL for the API. If None, defaults to http://localhost/v1
        user_id: User ID for the API request. If None, defaults to "user-id"
        timeout: Request timeout in seconds (default: 300)
        words: Optional list of word objects with timing information (deprecated, use sentences instead)
        sentences: Optional list of sentence objects with timing information
        
    Returns:
        Dictionary with:
            - "markdown_report": Summary text (markdown) from data.outputs.markdown_report
            - "events_markdown": Events markdown from data.outputs.events_markdown (if available, else None)
            - "pptx_base64": Base64-encoded PPTX file from data.outputs.pptx_base64 (if available, else None)
            - "marp_markdown": Marp markdown content from data.outputs.marp_markdown (if available, else None)
            - "ticker_recommendations": Ticker recommendations data from data.outputs.ticker_recommendations (if available, else None)
            - "ticker_marp_markdown": Ticker marp markdown content from data.outputs.ticker_marp_markdown (if available, else None)
        
    Raises:
        ValueError: If API key is not provided and not found in environment
        requests.RequestException: If API request fails
        KeyError: If response doesn't contain expected structure
    """
    # Get API key from parameter or environment
    api_key = api_key or os.getenv("DIFI_API_KEY")
    if not api_key:
        raise ValueError(
            "DIFI_API_KEY is required for Workflow API. "
            "Set it in .env file as DIFI_API_KEY or pass it to the function."
        )
    
    # Get base URL from parameter or environment, default to localhost
    base_url = base_url or os.getenv("DIFI_API_BASE_URL", "http://localhost/v1")
    # Ensure base_url doesn't end with /v1 if it's already there
    if base_url.endswith("/v1"):
        api_base = base_url
    elif base_url.endswith("/"):
        api_base = f"{base_url.rstrip('/')}/v1"
    else:
        api_base = f"{base_url}/v1"
    
    endpoint = f"{api_base}/workflows/run"
    user_id = user_id or os.getenv("DIFI_USER_ID", "user-id")
    
    # Prepare request
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Build inputs dict
    inputs = {
        "transcript": transcript,
        "source": source,
        "episode_title": episode_title
    }
    
    # Add sentences if provided (preferred over words)
    # Convert to JSON string as API expects string format
    if sentences is not None:
        import json
        inputs["sentences"] = json.dumps(sentences, ensure_ascii=False)
    elif words is not None:
        # Fallback to words for backward compatibility
        import json
        inputs["words"] = json.dumps(words, ensure_ascii=False)
    
    payload = {
        "inputs": inputs,
        "response_mode": "blocking",
        "user": user_id
    }
    
    # Make API request
    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=timeout
        )
        response.raise_for_status()  # Raise exception for bad status codes
        
        # Parse response
        response_data = response.json()
        
        # Check for null or empty response
        if response_data is None:
            raise ValueError("Workflow API returned null response")
        
        # Extract markdown_report from data.outputs.markdown_report
        if "data" not in response_data:
            raise KeyError(
                f"Response missing 'data' field. "
                f"Available keys: {list(response_data.keys())}. "
                f"Full response: {str(response_data)[:500]}"
            )
        
        data = response_data["data"]
        
        # Check if data is null
        if data is None:
            raise ValueError(
                f"Workflow API returned null data field. "
                f"Full response: {str(response_data)[:500]}"
            )
        
        if "outputs" not in data:
            raise KeyError(
                f"Response missing 'outputs' in data. "
                f"Available keys: {list(data.keys()) if isinstance(data, dict) else type(data)}. "
                f"Data value: {str(data)[:500]}"
            )
        
        outputs = data["outputs"]
        
        # Check if outputs is null
        if outputs is None:
            raise ValueError(
                f"Workflow API returned null outputs field. "
                f"Data: {str(data)[:500]}"
            )
        
        if "markdown_report" not in outputs:
            raise KeyError(
                f"Response missing 'markdown_report' in outputs. "
                f"Available keys: {list(outputs.keys()) if isinstance(outputs, dict) else type(outputs)}. "
                f"Outputs value: {str(outputs)[:500]}"
            )
        
        markdown_report = outputs["markdown_report"]
        
        # Check if markdown_report is null or empty
        if markdown_report is None:
            raise ValueError(
                f"Workflow API returned null markdown_report. "
                f"Outputs: {str(outputs)[:500]}"
            )
        
        if not markdown_report or (isinstance(markdown_report, str) and not markdown_report.strip()):
            raise ValueError(
                f"Workflow API returned empty markdown_report. "
                f"Outputs: {str(outputs)[:500]}"
            )
        
        # Extract events_markdown if available
        events_markdown = outputs.get("events_markdown")
        
        # Extract pptx_base64 and marp_markdown if available
        pptx_base64 = outputs.get("pptx_base64")
        marp_markdown = outputs.get("marp_markdown")
        
        # Extract ticker_recommendations and ticker_marp_markdown if available
        ticker_recommendations = outputs.get("ticker_recommendations")
        ticker_marp_markdown = outputs.get("ticker_marp_markdown")
        
        # Return dict with markdown_report, events_markdown, pptx_base64, marp_markdown, ticker_recommendations, and ticker_marp_markdown
        result = {
            "markdown_report": markdown_report,
            "events_markdown": events_markdown if events_markdown else None,
            "pptx_base64": pptx_base64 if pptx_base64 else None,
            "marp_markdown": marp_markdown if marp_markdown else None,
            "ticker_recommendations": ticker_recommendations if ticker_recommendations else None,
            "ticker_marp_markdown": ticker_marp_markdown if ticker_marp_markdown else None
        }
        
        return result
    
    except requests.exceptions.Timeout:
        raise requests.RequestException(
            f"Workflow API request timed out after {timeout} seconds. "
            "The workflow may be taking longer than expected."
        )
    except requests.exceptions.HTTPError as e:
        raise requests.RequestException(
            f"Workflow API request failed with status {response.status_code}: {e}. "
            f"Response: {response.text[:500]}"
        )
    except requests.exceptions.RequestException as e:
        raise requests.RequestException(
            f"Workflow API request failed: {e}"
        )
