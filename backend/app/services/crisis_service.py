"""
Crisis Detection Service
Keyword-based detection with 100% recall guarantee on known crisis phrases.
"""

CRISIS_KEYWORDS = [
    "suicide", "suicidal", "kill myself", "end my life", "want to die",
    "don't want to live", "no reason to live", "better off dead",
    "self harm", "self-harm", "hurt myself", "cutting myself", "cut myself",
    "overdose", "take pills", "can't go on", "give up on life",
    "nobody cares if i die", "nobody would care if i died", "worthless enough to die", "hopeless and want to die",
    "no point living", "worth living anymore", "ending it all", "end it all", "tired of living", "want it to end",
    "thinking about suicide", "planning to end", "method to kill",
]

CRISIS_RESPONSE = """I hear you, and I'm really glad you reached out. \
What you're feeling right now is serious, and you deserve immediate support \
from someone trained to help.

Please reach out right now:
• **iCall (India):** 9152987821
• **Vandrevala Foundation:** 1860-2662-345 (24/7, free)
• **NIMHANS Helpline:** 080-46110007
• **SNEHI:** 044-24640050
• **International:** https://www.findahelpline.com

You are not alone, and this feeling will not last forever. \
Are you safe right now? 💙"""


def is_crisis_message(text: str) -> bool:
    """
    Check if a message contains crisis indicators via keyword matching.
    100% recall on known crisis phrases — safety first.
    """
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in CRISIS_KEYWORDS)
