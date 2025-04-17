import json
import base64
import requests
from fastapi import APIRouter, Form, File, UploadFile
from fastapi.responses import JSONResponse
from newspaper import Article
from typing import List, Optional
import os
from dotenv import load_dotenv
from log_to_sheet import log_ad_check  # <-- Import logging utility

# Gemini API router
gemini_router = APIRouter()

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_MODEL = "gemini-1.5-pro-002"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

source_guidelines = {
    "adsense": "AdSense policies including misleading claims, clickbait, and low-value content.",
    "facebook": "Facebook Ads policies including personal attributes, sensational content, and prohibited products.",
    "google_ads": "Google Ads policies including destination requirements, misleading content, and restricted products.",
    "native": "Native platforms (Taboola/Outbrain) policies including brand safety, misleading claims, and inappropriate imagery.",
    "performance": "Performance-based evaluation such as clarity, call-to-action effectiveness, visual appeal, and emotional engagement."
}

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
    source: str = Form("adsense"),
    keywords: Optional[str] = Form(""),
    images: Optional[List[UploadFile]] = File(None),
):
    try:
        article_text = get_article_text(url)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"Failed to fetch article: {e}"})

    guideline_note = source_guidelines.get(source.lower(), "Ad platform compliance policies.")

    ad_text = f"Headline: {headline}\nDescription: {description}\nPrimary Text: {primary_text}"

    prompt = f"""
You are an expert in ad compliance.

Check the following ad for {guideline_note}

Given the article:
"/"/"/
{article_text[:3000]}
"/"/"/

And the following ad:
{ad_text}

Evaluate the ad for:
1. {source.capitalize()} policy compliance
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

        if raw_text.startswith("```json"):
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text.replace("```", "").strip()

        result = json.loads(raw_text)

        # 🔁 Log results to Google Sheets
        log_ad_check({
            "source": source,
            "url": url,
            "headline": headline,
            "description": description,
            "primary_text": primary_text,
            "keywords": keywords,
            "image_count": len(images) if images else 0,
            **result
        })

        return result

    except requests.exceptions.RequestException as e:
        print("❌ Gemini API request failed:", e)
        return JSONResponse(status_code=500, content={"error": str(e)})

    except json.JSONDecodeError as e:
        print("❌ Failed to parse Gemini response:", e)
        print("Raw response was:", raw_text)
        return JSONResponse(status_code=500, content={"error": "Gemini returned an invalid JSON format."})
