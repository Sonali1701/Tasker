# app.py
import streamlit as st
from datetime import datetime
import json, os, base64

# Firebase imports
import firebase_admin
from firebase_admin import credentials, firestore, auth

from ai_utils import ai_followup, ai_summarize, ai_rewrite

# -------- Streamlit page config --------
st.set_page_config(page_title="Team Tasker — AI Followups", layout="wide")
st.title("Team Tasker — Shared Tasks + AI Follow-ups")

# -------- Initialize Firebase Firestore & Auth --------
b64_str = st.secrets.get("FIREBASE_SERVICE_ACCOUNT_B64") or os.getenv("FIREBASE_SERVICE_ACCOUNT_B64")
if not b64_str:
    st.error("FIREBASE_SERVICE_ACCOUNT_B64 not found in Streamlit secrets or environment.")
    st.stop()

missing_padding = len(b64_str) % 4
if missing_padding:
    b64_str += "=" * (4 - missing_padding)


try:
    sa_info = json.loads(base64.b64decode(b64_str).decode("utf-8"))
except Exception as e:
    st.error(f"Invalid Base64 JSON: {e}")
    st.stop()

if not firebase_admin._apps:
    cred = credentials.Certificate(sa_info)
    firebase_admin.initialize_app(cred)
db = firestore.client()

# -------- Firestore Collections --------
TASKS_COLL = "tasks"
NOTES_COLL = "notes"

# -------- Helper Functions --------
def add_task_to_db(title, details, assigned_to, assigned_by, due_date):
    doc = {
        "title": title,
        "details": details or "",
        "assigned_to": assigned_to or "",
        "assigned_by": assigned_by or "",
        "due_date": due_date or "",
        "status": "Pending",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "ai_generated": False
    }
    db.collection(TASKS_COLL).add(doc)

def get_all_tasks():
    docs = db.collection(TASKS_COLL).order_by("due_date").stream()
    tasks = []
    for d in docs:
        data = d.to_dict()
        data["id"] = d.id
        tasks.append(data)
    return tasks

def update_task_status(task_id, new_status):
    db.collection(TASKS_COLL).document(task_id).update({
        "status": new_status,
        "updated_at": datetime.utcnow().isoformat()
    })

def add_ai_task(text):
    doc = {
        "title": text,
        "details": "",
        "assigned_to": "",
        "assigned_by": "AI",
        "due_date": "",
        "status": "Pending",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "ai_generated": True
    }
    db.collection(TASKS_COLL).add(doc)

def add_note_to_db(title, content, created_by):
    doc = {
        "title": title,
        "content": content,
        "created_by": created_by or "",
        "created_at": datetime.utcnow().isoformat()
    }
    db.collection(NOTES_COLL).add(doc)

def get_all_notes():
    docs = db.collection(NOTES_COLL).order_by("created_at", direction=firestore.Query.DESCENDING).stream()
    notes = []
    for d in docs:
        data = d.to_dict()
        data["id"] = d.id
        notes.append(data)
    return notes

# -------- User Authentication --------
if "user" not in st.session_state:
    st.session_state.user = None

def signup_user(email, password, display_name):
    try:
        user = auth.create_user(email=email, password=password, display_name=display_name)
        st.success("User signed up successfully! Please login now.")
    except Exception as e:
        st.error(f"Error signing up: {e}")

def login_user(email, password):
    try:
        # Firebase Admin SDK does not support password login directly
        # For production: use Firebase Authentication via frontend SDK or custom backend
        st.session_state.user = email
        st.success(f"Logged in as {email}")
    except Exception as e:
        st.error(f"Login failed: {e}")

with st.sidebar:
    st.header("User Authentication")
    if not st.session_state.user:
        auth_tab = st.radio("Choose action", ["Login", "Signup"])
        if auth_tab == "Signup":
            su_name = st.text_input("Display Name")
            su_email = st.text_input("Email")
            su_pass = st.text_input("Password", type="password")
            if st.button("Sign Up"):
                if su_name and su_email and su_pass:
                    signup_user(su_email, su_pass, su_name)
                else:
                    st.warning("All fields are required.")
        else:
            li_email = st.text_input("Email")
            li_pass = st.text_input("Password", type="password")
            if st.button("Login"):
                if li_email and li_pass:
                    login_user(li_email, li_pass)
                else:
                    st.warning("Email and password required.")
    else:
        st.write(f"Signed in as: **{st.session_state.user}**")
        if st.button("Logout"):
            st.session_state.user = None
            st.experimental_rerun()

st.markdown("---")
st.markdown("**Tips:**\n- Everyone sees a shared task board.\n- Assign using teammate names.\n- AI can generate follow-ups and add them as tasks.")

# -------- Navigation --------
if st.session_state.user:
    page = st.sidebar.radio("Navigate", ["Tasks", "Notes", "AI Playground", "Settings"])

    # ---------------- TASKS PAGE ----------------
    if page == "Tasks":
        st.header("Team Tasks")

        # Create new task
        with st.form("create_task_form", clear_on_submit=True):
            c1, c2 = st.columns([3,2])
            with c1:
                title = st.text_input("Task title")
                details = st.text_area("Details (optional)", height=100)
            with c2:
                assigned_to = st.text_input("Assign to (name)")
                due_date = st.date_input("Due date (optional)", value=None)
                submit = st.form_submit_button("Create Task")
            if submit:
                if not title.strip():
                    st.warning("Task title is required.")
                else:
                    due_str = due_date.isoformat() if due_date else ""
                    add_task_to_db(title.strip(), details.strip(), assigned_to.strip(), st.session_state.user, due_str)
                    st.success("Task created.")
                    st.experimental_rerun()

        st.markdown("---")

        # Filters & Display tasks
        all_tasks = get_all_tasks()
        colf1, colf2 = st.columns([1,2])
        with colf1:
            show_status = st.selectbox("Filter by status", ["All", "Pending", "In Progress", "Completed", "Snoozed"])
        with colf2:
            search_assignee = st.text_input("Filter by assignee (leave empty = all)")

        def matches_filter(t):
            if show_status != "All" and t.get("status", "") != show_status:
                return False
            if search_assignee and search_assignee.strip().lower() not in t.get("assigned_to","").lower():
                return False
            return True

        displayed = [t for t in all_tasks if matches_filter(t)]
        if not displayed:
            st.info("No tasks found (try clearing filters).")
        else:
            for t in displayed:
                cols = st.columns([4, 1, 1, 1, 1])
                left = cols[0]
                left.markdown(f"**{t.get('title')}**")
                if t.get("details"):
                    left.caption(t.get("details"))
                left.write(f"Assigned to: **{t.get('assigned_to') or '—'}**  •  Assigned by: {t.get('assigned_by') or '—'}")
                left.write(f"Due: {t.get('due_date') or '—'}  •  Status: {t.get('status') or '—'}")
                if t.get("ai_generated"):
                    left.write("_AI suggested_")

                # actions
                if st.button("Mark Done", key=f"done_{t['id']}"):
                    update_task_status(t["id"], "Completed")
                    st.success("Task marked completed.")
                    st.experimental_rerun()

                if st.button("Set In Progress", key=f"prog_{t['id']}"):
                    update_task_status(t["id"], "In Progress")
                    st.experimental_rerun()

                if st.button("AI Follow-Up", key=f"ai_{t['id']}"):
                    msg = ai_followup(t.get("title"), t.get("details",""), t.get("due_date",""))
                    for line in msg.splitlines():
                        line = line.strip("-*• \t")
                        if line:
                            add_ai_task(line)
                    st.success("AI follow-up added as task(s).")
                    st.experimental_rerun()

                st.write("---")

    # ---------------- NOTES PAGE ----------------
    elif page == "Notes":
        st.header("Shared Notes")
        with st.form("note_form", clear_on_submit=True):
            ntitle = st.text_input("Note title")
            ncontent = st.text_area("Note content", height=200)
            if st.form_submit_button("Save Note"):
                if not ntitle.strip() or not ncontent.strip():
                    st.warning("Title & content required.")
                else:
                    add_note_to_db(ntitle.strip(), ncontent.strip(), st.session_state.user)
                    st.success("Note saved.")
                    st.experimental_rerun()

        st.markdown("---")
        notes = get_all_notes()
        if not notes:
            st.info("No notes yet.")
        else:
            for n in notes:
                st.markdown(f"**{n.get('title')}** — _{n.get('created_by')}_")
                st.write(n.get("content"))
                st.write("---")

    # ---------------- AI PLAYGROUND ----------------
    elif page == "AI Playground":
        st.header("AI Playground")
        txt = st.text_area("Text to process", height=200)
        c1, c2, c3 = st.columns(3)
        if c1.button("Summarize"):
            out = ai_summarize(txt)
            st.write(out)
        if c2.button("Rewrite (professional)"):
            out = ai_rewrite(txt)
            st.write(out)
        if c3.button("AI Follow-up (for text)"):
            out = ai_followup(txt, "", "")
            st.write(out)

    # ---------------- SETTINGS ----------------
    elif page == "Settings":
        st.header("Settings & Notes")
        st.markdown("""
        - The app uses Firestore to store shared tasks/notes for the whole team.
        - Add your GEMINI_API_KEY and FIREBASE_SERVICE_ACCOUNT_B64 to Streamlit Secrets before deploying.
        - Users must login to see the shared tasks.
        """)

else:
    st.info("Please login or signup to access the app.")
