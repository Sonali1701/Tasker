import streamlit as st
from db import init_db, add_note, get_notes, add_task, get_tasks, update_task_status
from ai_utils import ai_summarize, ai_rewrite, ai_expand, ai_followup, ai_chat
from datetime import datetime

st.set_page_config(page_title="AI Workspace", layout="wide")
init_db()

st.title("🧠 AI-Based Notes & Task Follow-Up System (Gemini)")

menu = st.sidebar.radio("Navigation", ["📝 Notes", "✅ Tasks", "💬 AI Chat"])

# -------------------- NOTES --------------------
if menu == "📝 Notes":
    st.subheader("Write & Improve Notes")

    title = st.text_input("Note Title")
    content = st.text_area("Note Content", height=200)
    col1, col2, col3, col4 = st.columns(4)
    ai_output = ""

    if col1.button("💾 Save Note"):
        if title and content:
            add_note(title, content)
            st.success("Note saved successfully!")
        else:
            st.warning("Please enter both title and content.")

    if col2.button("🪄 Summarize"):
        ai_output = ai_summarize(content)
    if col3.button("✍️ Rewrite"):
        ai_output = ai_rewrite(content)
    if col4.button("💡 Expand"):
        ai_output = ai_expand(content)

    if ai_output:
        st.markdown("#### ✨ AI Output:")
        st.write(ai_output)

    st.divider()
    st.subheader("📚 All Notes")
    notes = get_notes()
    for note in notes:
        st.markdown(f"**{note[1]}** — *{note[3]}*")
        st.write(note[2])
        st.write("---")

# -------------------- TASKS --------------------
elif menu == "✅ Tasks":
    st.subheader("Manage Tasks & Get AI Follow-Ups")

    task = st.text_input("Task Description")
    deadline = st.date_input("Deadline")

    if st.button("Add Task"):
        if task.strip():
            add_task(task, deadline.strftime("%Y-%m-%d"))
            st.success("✅ Task added successfully!")
            st.rerun()
        else:
            st.warning("Please enter a task description.")

    st.divider()
    st.subheader("📋 Your Tasks")

    tasks = get_tasks()

    if not tasks:
        st.info("No tasks found. Add one above 👆")
    else:
        for t in tasks:
            task_id, task_text, due, status, created = t
            cols = st.columns([4, 2, 2, 2])

            with cols[0]:
                if status.lower() == "completed":
                    st.markdown(f"✅ ~~{task_text}~~ *(Due: {due})*")
                else:
                    st.markdown(f"🕓 **{task_text}** *(Due: {due})*")

            with cols[1]:
                st.write(status)

            with cols[2]:
                if status.lower() != "completed":
                    if st.button("✅ Mark Done", key=f"done_{task_id}"):
                        update_task_status(task_id, "Completed")
                        st.success(f"Task '{task_text}' marked as done!")
                        st.rerun()

            with cols[3]:
                if st.button("🤖 Follow-Up", key=f"follow_{task_id}"):
                    msg = ai_followup(task_text, due)
                    if msg:
                        # Add the AI-generated follow-up as a new task
                        add_task(msg.strip(), datetime.now().strftime("%Y-%m-%d"))
                        st.success("✨ AI generated a new follow-up task!")
                        st.rerun()

            st.write("---")
# -------------------- AI CHAT --------------------
elif menu == "💬 AI Chat":
    st.subheader("Chat with your Notes & Tasks")
    query = st.text_area("Ask something...", height=100)

    notes = [n[2] for n in get_notes()]
    tasks = [t[1] + " (Due: " + t[2] + ")" for t in get_tasks()]
    context = "\n".join(notes + tasks)

    if st.button("Ask AI"):
        if query.strip():
            response = ai_chat(f"Context:\n{context}\n\nUser Query:\n{query}")
            st.markdown("#### 🧠 AI Response:")
            st.write(response)
        else:
            st.warning("Please enter a question.")
