import io
import base64
import json
from fastapi import FastAPI, UploadFile, File, Form, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from newspaper import Article
import openai
from api import API_KEY

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

openai.api_key = API_KEY

rewrite_router = APIRouter()


def get_article_text(url: str) -> str:
    article = Article(url)
    article.download()
    article.parse()
    return article.text


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
        return {"error": f"Failed to fetch article: {e}"}

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
        print("✅ Article loaded, preparing to call GPT")
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that rewrites ads to make them compliant."},
                {"role": "user", "content": prompt.strip()}
            ],
            max_tokens=600,
            temperature=0.7
        )

        print("RAW OpenAI Response:", response)

        if not response.choices or not response.choices[0].message:
            return {"error": "Empty response from GPT."}

        reply = response.choices[0].message.content.strip()
        print("GPT Rewritten Ad Response:", reply)

        if reply.startswith("```json"):
            reply = reply.replace("```json", "").replace("```", "").strip()
        elif reply.startswith("```"):
            reply = reply.replace("```", "").strip()

        return json.loads(reply)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"Failed to parse GPT response: {e}"}


router = rewrite_router
app.include_router(router)
