# ai_utils.py
import os
import streamlit as st
import google.generativeai as genai

# Load Gemini key from Streamlit secrets or env
API_KEY = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
if not API_KEY:
    # In local dev this will print warning but app keeps running
    st.warning("GEMINI_API_KEY not found in secrets or environment. AI features will not work.")
else:
    genai.configure(api_key=API_KEY)

def gemini_generate(prompt: str, model_name: str = "gemini-1.5-flash", max_tokens: int = 300) -> str:
    """Generic wrapper to call Gemini via google-generativeai."""
    if not API_KEY:
        return "⚠️ Gemini key missing — cannot generate AI content."
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            prompt,
            max_output_tokens=max_tokens
        )
        # response.text works for regular responses
        return getattr(response, "text", "") or "⚠️ No content returned by Gemini."
    except Exception as e:
        return f"❌ AI Error: {e}"

def ai_followup(task_title: str, details: str = None, due_date: str = None) -> str:
    """Return a short set of follow-up tasks / reminder as a bullet list."""
    prompt = (
        f"You are an assistant that creates short, actionable follow-up tasks or reminder messages.\n\n"
        f"Task: {task_title}\n"
    )
    if details:
        prompt += f"Details: {details}\n"
    if due_date:
        prompt += f"Due date: {due_date}\n"
    prompt += "\nGenerate 2-3 short bullet points (each 1-line) that are actionable follow-ups or next steps."
    return gemini_generate(prompt)

def ai_summarize(text: str) -> str:
    if not text:
        return "No text provided."
    prompt = f"Summarize the following text in 2-3 short sentences:\n\n{text}"
    return gemini_generate(prompt)

def ai_rewrite(text: str, instruction: str = "Make it concise and professional.") -> str:
    if not text:
        return "No text provided."
    prompt = f"Rewrite the following text. Instruction: {instruction}\n\n{text}"
    return gemini_generate(prompt)
