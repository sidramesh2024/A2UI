# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging
import os

from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)

# JSON schema for Gemini structured output - matches the UI's expected format
RESTAURANT_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Restaurant name"},
            "detail": {"type": "string", "description": "Short description of the restaurant"},
            "address": {"type": "string", "description": "Full street address"},
            "rating": {"type": "string", "description": "Star rating e.g. ★★★★☆"},
            "infoLink": {"type": "string", "description": "Markdown link format: [More Info](https://example.com)"},
        },
        "required": ["name", "detail", "address", "rating", "infoLink"],
    },
}


def _fetch_restaurants_via_gemini(
    cuisine: str, location: str, count: int, base_url: str
) -> list[dict]:
    """Use Gemini API to fetch real restaurant data from the model's knowledge."""
    try:
        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("  - GEMINI_API_KEY not set, cannot fetch real data")
            return []

        client = genai.Client(api_key=api_key)

        location_display = location.strip() if location and location.strip() else "New York"
        cuisine_display = cuisine.strip() if cuisine and cuisine.strip() else "various"

        prompt = f"""List {count} real, well-known {cuisine_display} restaurants in {location_display}.

For each restaurant provide:
- name: The actual restaurant name
- detail: A brief one-sentence description (cuisine style, ambiance, or specialty)
- address: Full street address with city and state/country
- rating: Star rating as 4-5 characters using ★ and ☆ (e.g. ★★★★☆)
- infoLink: A markdown link to the restaurant's website or Google Maps in format [More Info](URL). Use the real website if known, otherwise use a Google Maps search URL like https://www.google.com/maps/search/?api=1&query=<restaurant+name+address>

Return only real restaurants that exist. Use your knowledge of actual establishments."""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RESTAURANT_SCHEMA,
            ),
        )

        if not response.text or not response.text.strip():
            logger.warning("  - Gemini returned empty response")
            return []

        data = json.loads(response.text.strip())
        if not isinstance(data, list):
            data = [data] if isinstance(data, dict) else []

        # Add imageUrl (placeholder - we don't have real images from Gemini)
        placeholder_image = f"{base_url}/static/logo.png" if base_url else "http://localhost:10002/static/logo.png"
        for item in data:
            if "imageUrl" not in item:
                item["imageUrl"] = placeholder_image

        logger.info(f"  - Gemini returned {len(data)} real restaurants")
        return data[:count]

    except Exception as e:
        logger.error(f"  - Gemini API error: {e}")
        return []


def _get_fallback_restaurants(
    cuisine: str, location: str, count: int, tool_context: ToolContext
) -> list[dict]:
    """Fallback to hardcoded data when Gemini is unavailable."""
    location_lower = (location or "").lower()
    is_supported = (
        "new york" in location_lower
        or "ny" in location_lower
        or "near me" in location_lower
        or not location_lower.strip()
    )

    if not is_supported:
        return []

    try:
        script_dir = os.path.dirname(__file__)
        file_path = os.path.join(script_dir, "restaurant_data.json")
        with open(file_path) as f:
            data_str = f.read()
            if base_url := tool_context.state.get("base_url"):
                data_str = data_str.replace("http://localhost:10002", base_url)
            all_items = json.loads(data_str)

        target_cuisine = (cuisine or "").strip().lower()
        if target_cuisine:
            filtered = [
                r for r in all_items
                if r.get("cuisine", "").lower() == target_cuisine
            ]
        else:
            filtered = all_items

        return filtered[:count]
    except Exception as e:
        logger.error(f"  - Fallback data error: {e}")
        return []


def get_restaurants(
    cuisine: str, location: str, tool_context: ToolContext, count: int = 5
) -> str:
    """Call this tool to get a list of restaurants based on a cuisine and location.
    Uses Gemini API for real restaurant data when GEMINI_API_KEY is set.
    Falls back to hardcoded demo data if the API is unavailable.
    'count' is the number of restaurants to return.
    """
    logger.info(f"--- TOOL CALLED: get_restaurants (count: {count}) ---")
    logger.info(f"  - Cuisine: {cuisine}")
    logger.info(f"  - Location: {location}")

    base_url = tool_context.state.get("base_url", "http://localhost:10002")
    items = []

    # Try Gemini first for real data
    if os.getenv("GEMINI_API_KEY"):
        items = _fetch_restaurants_via_gemini(
            cuisine=cuisine or "various",
            location=location or "New York",
            count=count,
            base_url=base_url,
        )

    # Fallback to hardcoded data if Gemini returned nothing
    if not items:
        logger.info("  - Using fallback hardcoded data")
        items = _get_fallback_restaurants(cuisine, location, count, tool_context)

    logger.info(f"  - Returning {len(items)} restaurants")
    return json.dumps(items)
