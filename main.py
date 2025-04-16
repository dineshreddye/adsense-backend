import io
import base64
import json
import openai
from fastapi import FastAPI, UploadFile, File, Form, APIRouter
from analyze_with_gemini import gemini_router  
from rewrite_ad_with_gpt import router as rewrite_router
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from newspaper import Article
import os

app = FastAPI()
app.include_router(rewrite_router)
app.include_router(gemini_router)  # ✅ Add this


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

openai.api_key = os.getenv("OPENAI_API_KEY")

rewrite_router = APIRouter()


def get_article_text(url: str) -> str:
    article = Article(url)
    article.download()
    article.parse()
    return article.text


def encode_image_to_base64(image_file: UploadFile) -> str:
    image_data = image_file.file.read()
    base64_image = base64.b64encode(image_data).decode("utf-8")
    return f"data:image/jpeg;base64,{base64_image}"


@rewrite_router.post("/analyze_with_gpt")
async def analyze_with_gpt(
    url: str = Form(...),
    headline: str = Form(...),
    description: str = Form(...),
    primary_text: str = Form(...),
    images: Optional[List[UploadFile]] = File(None),
):
    try:
        article_text = get_article_text(url)
    except Exception as e:
        return {"error": f"Failed to fetch article: {e}"}

    ad_text = f"Headline: {headline}\nDescription: {description}\nPrimary Text: {primary_text}"
    prompt = f"""
You are an expert in AdSense compliance and ad relevance checking.

Given the article:
\"\"\"
{article_text[:3000]}
\"\"\"

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

    messages = [
        {"role": "system", "content": "You are a helpful assistant that analyzes ads for policy and relevance."},
        {"role": "user", "content": prompt.strip()}
    ]

    try:
        if images:
            base64_img = encode_image_to_base64(images[0])
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=messages + [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": base64_img}}
                        ]
                    }
                ],
                max_tokens=1000,
                temperature=0.4
            )
        else:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=messages,
                max_tokens=1000,
                temperature=0.4
            )

        reply = response.choices[0].message.content.strip()

        usage = response.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

        # gpt-4o pricing (as of April 2024): $5/m for input, $15/m for output
        cost = (prompt_tokens / 1000 * 0.005) + (completion_tokens / 1000 * 0.015)
        print("GPT Analysis Response:", reply)

        if reply.startswith("```json"):
            reply = reply.replace("```json", "").replace("```", "").strip()
        elif reply.startswith("```"):
            reply = reply.replace("```", "").strip()

        result = json.loads(reply)
        result["cost_usd"] = round(cost, 6)
        result["tokens"] = {
            "prompt": prompt_tokens,
            "completion": completion_tokens,
            "total": total_tokens
        }
        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"Failed to process GPT response: {e}"}


router = rewrite_router
app.include_router(router)
