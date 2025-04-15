import json
import base64
import requests
from fastapi import APIRouter, Form, File, UploadFile
from fastapi.responses import JSONResponse
from newspaper import Article
from typing import List, Optional
from api import GEMINI_API_KEY


gemini_router = APIRouter()

GEMINI_MODEL = "gemini-1.5-pro-002"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"


def get_article_text(url: str) -> str:
    article = Article(url)
    article.download()
    article.parse()
    return article.text


def encode_image_to_base64(image_file: UploadFile) -> dict:
    image_data = image_file.file.read()
    base64_image = base64.b64encode(image_data).decode("utf-8")
    return {
        "inlineData": {
            "mimeType": image_file.content_type,
            "data": base64_image
        }
    }


@gemini_router.post("/analyze_with_gemini")
async def analyze_with_gemini(
    url: str = Form(...),
    headline: str = Form(...),
    description: str = Form(...),
    primary_text: str = Form(...),
    images: Optional[List[UploadFile]] = File(None),
):
    try:
        article_text = get_article_text(url)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"Failed to fetch article: {e}"})

    ad_text = f"Headline: {headline}\nDescription: {description}\nPrimary Text: {primary_text}"

    prompt = f"""
You are an expert in AdSense compliance and ad relevance checking.

Given the article:
"/"/"/
{article_text[:3000]}
"/"/"

And the following ad:
{ad_text}

Evaluate the ad for:
1. AdSense policy compliance
2. Relevance to the article
3. Suggestions for improvement
4. Image relevance and compliance (if provided)

Respond in this JSON format:
{{
  "compliant": true/false,
  "relevancy_score": 0-100,
  "image_score": 0-100,
  "issues": ["..."],
  "suggestions": ["..."]
}}

Only return the JSON object — no explanation or markdown.
"""

    parts = [{"text": prompt.strip()}]
    if images:
        parts.append(encode_image_to_base64(images[0]))

    payload = {
        "contents": [
            {
                "parts": parts
            }
        ]
    }

    try:
        headers = {
            "Content-Type": "application/json",
        }

        response = requests.post(GEMINI_URL, headers=headers, json=payload)
        response.raise_for_status()

        raw_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        print("✅ Gemini response received:", json.dumps(response.json(), indent=2))

        # Remove markdown formatting
        if raw_text.startswith("```json"):
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text.replace("```", "").strip()

        result = json.loads(raw_text)
        return result

    except requests.exceptions.RequestException as e:
        print("❌ Gemini API request failed:", e)
        return JSONResponse(status_code=500, content={"error": str(e)})

    except json.JSONDecodeError as e:
        print("❌ Failed to parse Gemini response:", e)
        print("Raw response was:", raw_text)
        return JSONResponse(status_code=500, content={"error": "Gemini returned an invalid JSON format."})