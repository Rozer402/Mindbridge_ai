"""
AI Service — Main Orchestrator
Implements the full 8-step pipeline from the IEEE ICDSBS 2025 paper:
1. Embed → 2. Relevance Check → 3. Crisis Detection →
4. Few-Shot Retrieval → 5. Build Prompt → 6. Generate → 7. Stream → 8. Persist
"""

import google.generativeai as genai
from .embedder import embedder
from .crisis_service import is_crisis_message, CRISIS_RESPONSE
from app.config import settings
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are MindBridge, a compassionate AI mental health companion. Your role is to provide empathetic, supportive, non-judgmental responses to people dealing with mental health challenges.

Core principles:
- Always validate the user's feelings FIRST before offering any perspective
- Use open-ended questions to encourage self-reflection and exploration
- NEVER diagnose any mental health condition or prescribe medication
- Always recommend professional help for persistent or serious issues
- Keep your tone warm, calm, supportive, and hopeful
- Responses should be 2-4 sentences unless the user clearly needs more
- Use "I" statements and second-person language to feel personal ("I can hear that..." / "It sounds like you...")
- Never minimize feelings — everything the user shares matters

Topic steering & Context:
- Maintain conversation continuity. Always factor in previous messages.
- If the user asks something completely off-topic (like coding, math, or random trivia), respond politely but gently steer the conversation back to their emotional state or wellbeing. Do not abruptly reject them.
- You are NOT a replacement for therapy. You are a first point of empathetic support."""

STATIC_EXAMPLES = [
    {
        "user": "I feel overwhelmed and don't know what to do.",
        "assistant": "That sounds really exhausting — feeling overwhelmed takes so much out of you, and I can hear how heavy this feels right now. You don't have to figure everything out at once. Can you tell me what's weighing on you the most right now?"
    },
    {
        "user": "I've been anxious about everything lately.",
        "assistant": "Anxiety can be so consuming, especially when it feels like it's everywhere at once — like your mind won't let you rest. You're not alone in feeling this way. What situation feels most pressing or difficult for you today?"
    },
    {
        "user": "I feel like no one understands me.",
        "assistant": "That feeling of being misunderstood can be really lonely and painful. You deserve to be heard and seen for who you truly are. Can you tell me more about what's been happening that's made you feel this way?"
    }
]

OFF_TOPIC_RESPONSE = (
    "I'm here specifically to support your mental and emotional wellbeing. "
    "It sounds like your question might be about something else — and I may not be "
    "the best resource for that. Is there something on your mind emotionally "
    "that I can help with? I'm here to listen. 💙"
)


def _initialize_gemini():
    """Configure Gemini API. Call once at startup."""
    if settings.GEMINI_API_KEY:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        logger.info("[AI Service] Gemini API configured.")
    else:
        logger.warning("[AI Service] No GEMINI_API_KEY found. AI responses will use fallback.")


async def process_message(
    user_message: str,
    session_history: list[dict]
) -> dict:
    """
    Full AI pipeline. Returns:
    {
        "response": str,
        "is_crisis": bool,
        "is_relevant": bool,
        "relevance_score": float,
        "few_shot_count": int
    }
    """
    # Step 1: Sanitize input
    user_message = user_message.strip()[:1000]

    # Step 2: Embed the message
    query_vec = embedder.embed(user_message)

    # Step 3: Relevance Check (Soft tracking only)
    is_relevant, relevance_score = embedder.check_relevance(query_vec)
    
    # We no longer hard-reject based on relevance_score. 
    # Hard-filtering breaks conversation continuity (e.g. "I don't know", "Yes", or follow-up questions).
    # Instead, we let the LLM system prompt handle gentle steering if the topic truly drifts.

    # Step 4: Crisis detection (keyword + embedding)
    if is_crisis_message(user_message) or embedder.check_crisis_embedding(query_vec):
        return {
            "response": CRISIS_RESPONSE,
            "is_crisis": True,
            "is_relevant": True,
            "relevance_score": relevance_score,
            "few_shot_count": 0
        }

    # Step 5: Retrieve dynamic few-shot examples
    examples = embedder.get_few_shot_examples(query_vec)

    # Step 6: Build Gemini message history
    messages = []

    # Static examples (always included)
    for ex in STATIC_EXAMPLES:
        messages.append({"role": "user", "parts": [ex["user"]]})
        messages.append({"role": "model", "parts": [ex["assistant"]]})

    # Dynamic examples (retrieved by embedding similarity)
    for ex in examples:
        if ex.get("category") != "crisis":  # Never use crisis examples as few-shot
            messages.append({"role": "user", "parts": [ex["context"]]})
            messages.append({"role": "model", "parts": [ex["response"]]})

    # Session history (last 8 messages for context window)
    for msg in session_history[-8:]:
        role = "user" if msg["role"] == "user" else "model"
        messages.append({"role": role, "parts": [msg["content"]]})

    # Current user message
    messages.append({"role": "user", "parts": [user_message]})

    # Step 7: Generate with Gemini
    try:
        if not settings.GEMINI_API_KEY:
            raise ValueError("No API key")

        model = genai.GenerativeModel(
            "gemini-2.5-flash",
            system_instruction=SYSTEM_PROMPT
        )
        response = model.generate_content(messages)
        ai_text = response.text

    except Exception as e:
        logger.error(f"[AI Service] Gemini error: {e}")
        # Graceful fallback — use the best few-shot example response if available
        if examples:
            ai_text = examples[0].get("response", "")
        elif session_history:
            # Mirror empathy from a static example
            ai_text = STATIC_EXAMPLES[0]["assistant"]
        else:
            ai_text = (
                "I hear you, and what you're sharing matters. "
                "Can you tell me more about what's been on your mind? "
                "I'm here to listen. 💙"
            )

    return {
        "response": ai_text,
        "is_crisis": False,
        "is_relevant": True,
        "relevance_score": relevance_score,
        "few_shot_count": len(examples)
    }
