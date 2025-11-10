import streamlit as st
import os
import google.generativeai as genai

# ✅ Load Gemini API key
api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")

# ✅ Configure Gemini
genai.configure(api_key=api_key)

# ---------------- COMMON GENERATION FUNCTION ----------------
def gemini_generate(prompt: str):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")  # Use 1.5-pro for deeper reasoning
        response = model.generate_content(prompt)
        return response.text if hasattr(response, "text") else "⚠️ No response generated."
    except Exception as e:
        return f"❌ Error: {str(e)}"

# ---------------- AI UTILITY FUNCTIONS ----------------
def ai_summarize(text):
    """Summarize text clearly."""
    return gemini_generate(f"Summarize this text clearly:\n\n{text}")

def ai_rewrite(text):
    """Rewrite text in a more professional tone."""
    return gemini_generate(f"Rewrite this text in a more professional tone:\n\n{text}")

def ai_expand(text):
    """Expand text with more details and clarity."""
    return gemini_generate(f"Expand on this idea with more details and clarity:\n\n{text}")

def ai_followup(task, due_date=None):
    """Generate actionable follow-up suggestions for a task."""
    prompt = f"Generate 2–3 clear, actionable follow-up tasks for:\n\nTask: {task}"
    if due_date:
        prompt += f"\nDue Date: {due_date}"
    prompt += "\nFormat output as short bullet points."
    return gemini_generate(prompt)

def ai_chat(prompt):
    """General chat with Gemini model."""
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        return response.text if hasattr(response, "text") else "⚠️ No response generated."
    except Exception as e:
        return f"❌ Error: {str(e)}"
