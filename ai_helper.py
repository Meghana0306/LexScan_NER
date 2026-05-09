# ══════════════════════════════════════════════════════
#  ai_helper.py — AI Backend (swap models here easily)
#  Change the MODEL variable below to switch models.
#  app.py imports this — never touch app.py for AI changes
# ══════════════════════════════════════════════════════

import os
import httpx
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)

# ── CHANGE THIS LINE TO SWITCH MODELS ──────────────────
MODEL = "llama-3.3-70b-versatile"  # options: llama3-70b-8192, mixtral-8x7b-32768, gemma2-9b-it
# ───────────────────────────────────────────────────────

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

def ask_ai(messages: list, system_prompt: str) -> str:
    """
    Send messages to AI and get a response.
    messages = list of {"role": "user"/"assistant", "content": "..."}
    """
    if not GROQ_API_KEY:
        return "❌ Add GROQ_API_KEY=your_key to your .env file."
    try:
        groq_messages = [{"role": "system", "content": system_prompt}]
        for m in messages:
            role = m.get("role", "user") if isinstance(m, dict) else "user"
            text = m.get("content", str(m)) if isinstance(m, dict) else str(m)
            groq_messages.append({"role": role, "content": text})

        resp = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={"model": MODEL, "messages": groq_messages, "max_tokens": 1000},
            timeout=30
        )
        data = resp.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        elif "error" in data:
            err = data["error"]
            msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            return f"Groq Error: {msg}"
        return f"Unexpected: {str(data)[:200]}"
    except Exception as e:
        return f"Error: {str(e)}"
