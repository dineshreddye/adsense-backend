import os
import openai
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from analyze_with_gemini import gemini_router
from rewrite_ad_with_gpt import router as rewrite_router

# Initialize FastAPI app
app = FastAPI()

# Include routers
app.include_router(gemini_router)
app.include_router(rewrite_router)

# Enable CORS for Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with ["https://your-vercel-app.vercel.app"] for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load OpenAI key from environment
openai.api_key = os.getenv("OPENAI_API_KEY")

# Healthcheck route
@app.get("/", response_class=HTMLResponse)
def root():
    return "<h3>✅ AdChecker backend is live</h3>"
