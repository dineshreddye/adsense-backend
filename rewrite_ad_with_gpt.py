import io
import base64
import json
import openai
from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse
from newspaper import Article
import os
from dotenv import load_dotenv

# Set OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# Create FastAPI router
rewrite_router = APIRouter()

# Helper to fetch article content
def get_article_text(url: str) -> str:
    article = Article(url)
    article.download()
    article.parse()
    return article.text

# Ad rewriting endpoint
@rewrite_router.post("/rewrite_ad_with_gpt")
async def rewrite_ad_with_gpt(
    url: str = Form(...),
    headline: str = Form(...),
    description: str = Form(...),
    primary_text: str = Form(...),
):
    try:
        article_text = get_article_text(url)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"Failed to fetch article: {e}"})

    user_ad = f"Headline: {headline}\nDescription: {description}\nPrimary Text: {primary_text}"

    prompt = f"""
You are an expert ad copywriter and policy reviewer.

Given the article:
\"\"\"
{article_text[:3000]}
\"\"\"

And this non-compliant or poorly performing ad:
{user_ad}

Rewrite the ad to be:
- Fully compliant with AdSense policies
- Relevant to the article
- Clear and compelling

Return only a pure JSON object.
DO NOT include markdown, code blocks, or any explanation.
Only return this format:
{{"headline": "...", "description": "...", "primary_text": "..."}}
"""

    try:
        print("✅ Sending to GPT...")
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that rewrites ads to make them compliant."},
                {"role": "user", "content": prompt.strip()}
            ],
            max_tokens=600,
            temperature=0.7
        )

        reply = response.choices[0].message.content.strip()

        # Clean up any formatting
        if reply.startswith("```json"):
            reply = reply.replace("```json", "").replace("```", "").strip()
        elif reply.startswith("```"):
            reply = reply.replace("```", "").strip()

        return JSONResponse(content=json.loads(reply))

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "Failed to process GPT response."})

# ✅ Export the router
router = rewrite_router
