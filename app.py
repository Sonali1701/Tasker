import streamlit as st
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore
import json, base64, requests
from datetime import datetime
from email.mime.text import MIMEText
import smtplib

# --- PAGE CONFIG ---
st.set_page_config(page_title="Team Tasker", layout="wide")

# --- FIREBASE INITIALIZATION ---
if not firebase_admin._apps:
    try:
        FIREBASE_SERVICE_ACCOUNT_B64 = st.secrets.get("FIREBASE_SERVICE_ACCOUNT_B64", "")
        FIREBASE_WEB_API_KEY = st.secrets.get("FIREBASE_WEB_API_KEY", "")
        if not FIREBASE_SERVICE_ACCOUNT_B64:
            raise ValueError("Missing FIREBASE_SERVICE_ACCOUNT_B64 in secrets")

        decoded_json = base64.b64decode(FIREBASE_SERVICE_ACCOUNT_B64).decode("utf-8")
        service_account_info = json.loads(decoded_json)
        cred = credentials.Certificate(service_account_info)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
    except Exception as e:
        st.error(f"❌ Firebase initialization failed: {e}")
        st.stop()
else:
    db = firestore.client()

# --- GOOGLE GEMINI ---
genai.configure(api_key=st.secrets.get("GOOGLE_API_KEY", ""))
model = genai.GenerativeModel("gemini-2.5-flash")

# --- EMAIL SETUP (GMAIL APP PASSWORD) ---
EMAIL_SENDER = st.secrets.get("EMAIL_SENDER")
EMAIL_PASSWORD = st.secrets.get("EMAIL_APP_PASSWORD")

def send_email(to_emails, subject, message):
    try:
        msg = MIMEText(message, "html")
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = ", ".join(to_emails)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, to_emails, msg.as_string())
        return True
    except Exception as e:
        st.error(f"Email error: {e}")
        return False

# --- AI HELPERS ---
def ai_followup(task_text):
    try:
        response = model.generate_content(f"Generate a short follow-up message for: {task_text}")
        return response.text.strip()
    except Exception as e:
        return f"❌ AI Error: {e}"

def ai_chat(query):
    try:
        response = model.generate_content(query)
        return response.text.strip()
    except Exception as e:
        return f"❌ AI Error: {e}"

# --- FIRESTORE HELPERS ---
def add_task(task, assigned_to, assigned_by, due_date, status="Pending"):
    db.collection("tasks").add({
        "task": task,
        "assigned_to": assigned_to,
        "assigned_by": assigned_by,
        "due_date": due_date,
        "status": status,
        "timestamp": datetime.now().isoformat()
    })

def get_all_tasks():
    return [doc.to_dict() | {"id": doc.id} for doc in db.collection("tasks").stream()]

def add_meeting(title, date, link, attendees, created_by):
    db.collection("meetings").add({
        "title": title,
        "date": date,
        "link": link,
        "attendees": attendees,
        "created_by": created_by,
        "timestamp": datetime.now().isoformat()
    })

def get_meetings():
    docs = db.collection("meetings").order_by("date").stream()
    return [d.to_dict() for d in docs]

def add_note(user, note):
    db.collection("notes").add({
        "user": user,
        "note": note,
        "timestamp": datetime.now().isoformat()
    })

def get_notes(user):
    docs = db.collection("notes").where("user", "==", user).stream()
    return [d.to_dict() for d in docs]

def add_travel_plan(from_city, to_city, traveller, date, ticket_url, added_by):
    db.collection("travels").add({
        "from_city": from_city,
        "to_city": to_city,
        "traveller": traveller,
        "date": date,
        "ticket_url": ticket_url,
        "added_by": added_by,
        "timestamp": datetime.now().isoformat()
    })

def get_travel_plans():
    docs = db.collection("travels").order_by("date").stream()
    return [d.to_dict() for d in docs]

# --- AUTHENTICATION ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "email" not in st.session_state:
    st.session_state.email = None

st.sidebar.title("🔐 Team Login")

def verify_user(email, password):
    FIREBASE_WEB_API_KEY = st.secrets.get("FIREBASE_WEB_API_KEY", "")
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    response = requests.post(url, json=payload)
    return response.status_code == 200

if not st.session_state.logged_in:
    choice = st.sidebar.radio("Select", ["Login", "Sign Up"])
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")

    if choice == "Sign Up":
        if st.sidebar.button("Create Account"):
            try:
                url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={st.secrets['FIREBASE_WEB_API_KEY']}"
                res = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True})
                if res.status_code == 200:
                    st.sidebar.success("✅ Account created! Please log in.")
                else:
                    st.sidebar.error(res.json().get("error", {}).get("message", "Error"))
            except Exception as e:
                st.sidebar.error(e)
    else:
        if st.sidebar.button("Login"):
            if verify_user(email, password):
                st.session_state.logged_in = True
                st.session_state.email = email
                st.sidebar.success(f"✅ Logged in as {email}")
                st.rerun()
            else:
                st.sidebar.error("Invalid email or password.")
else:
    st.sidebar.success(f"Welcome, {st.session_state.email} 👋")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.email = None
        st.rerun()

if not st.session_state.logged_in:
    st.info("👋 Please log in to continue.")
    st.stop()

email = st.session_state.email

# --- SIDEBAR DASHBOARD ---
st.sidebar.markdown("---")
st.sidebar.subheader("📋 Pending Tasks")
tasks = [t for t in get_all_tasks() if t["status"] == "Pending"]
for t in tasks[:5]:
    st.sidebar.markdown(f"- {t['task']} ({t['assigned_to']})")

st.sidebar.markdown("---")
st.sidebar.subheader("📅 Upcoming Meetings")
meetings = [m for m in get_meetings()]
for m in meetings[:5]:
    st.sidebar.markdown(f"- {m['title']} on {m['date']}")

# --- MAIN TABS ---
tabs = st.tabs(["📋 Tasks", "📝 Notes", "💬 AI Playground", "📅 Meetings", "✈️ Travel Plans"])

# --- TASK TAB ---
with tabs[0]:
    st.header("📋 Team Tasks")
    task = st.text_input("Task Description")
    assigned_to = st.text_input("Assigned To (Email)")
    due_date = st.date_input("Due Date")

    if st.button("Add Task"):
        if task and assigned_to:
            add_task(task, assigned_to, email, str(due_date))
            st.success("✅ Task Added!")
            st.rerun()
        else:
            st.warning("Please fill all fields before adding a task.")

    st.subheader("All Tasks")
    for t in get_all_tasks():
        st.markdown(f"**{t['task']}** — *{t['assigned_to']}* | 📅 {t['due_date']} | Status: {t['status']}")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button(f"✅ Done ({t['task']})"):
                db.collection("tasks").document(t["id"]).update({"status": "Done"})
                st.rerun()
        with col2:
            if st.button(f"🤖 Follow-up ({t['task']})"):
                st.info(ai_followup(t['task']))

# --- NOTES TAB ---
with tabs[1]:
    st.header("📝 Notes")
    note = st.text_area("Write a note")
    if st.button("Save Note"):
        add_note(email, note)
        st.success("✅ Note saved!")
        st.rerun()

    for n in get_notes(email):
        st.markdown(f"- {n['note']}  \n🕒 {n['timestamp']}")

# --- AI PLAYGROUND ---
with tabs[2]:
    st.header("💬 AI Playground")
    query = st.text_area("Ask the AI Assistant")
    if st.button("Ask AI"):
        reply = ai_chat(query)
        st.markdown(f"**AI:** {reply}")

# --- MEETINGS TAB ---
with tabs[3]:
    st.header("📅 Team Meetings")
    m_title = st.text_input("Meeting Title")
    m_date = st.date_input("Meeting Date")
    m_link = st.text_input("Meeting Link")
    m_attendees = st.text_input("Attendees (comma-separated emails)")

    if st.button("Add Meeting"):
        attendees = [a.strip() for a in m_attendees.split(",") if a.strip()]
        add_meeting(m_title, str(m_date), m_link, attendees, email)
        st.success("✅ Meeting Added!")

        email_body = f"""
        <h3>Meeting Scheduled: {m_title}</h3>
        <p>Date: {m_date}</p>
        <p>Link: <a href='{m_link}'>Join Here</a></p>
        <p>Scheduled by: {email}</p>
        """
        send_email(attendees, f"Meeting Invite: {m_title}", email_body)
        st.info("📧 Email invites sent!")
        st.rerun()

    for m in get_meetings():
        st.markdown(f"📌 **{m['title']}** — {m['date']}  \n🔗 [Join Meeting]({m['link']})")

# --- TRAVEL TAB ---
with tabs[4]:
    st.header("✈️ Travel Management")
    from_city = st.text_input("From")
    to_city = st.text_input("To")
    traveller = st.text_input("Traveller Name")
    t_date = st.date_input("Travel Date")
    ticket_url = st.text_input("Ticket Link (e.g., from MakeMyTrip)")

    if st.button("Add Travel Plan"):
        add_travel_plan(from_city, to_city, traveller, str(t_date), ticket_url, email)
        st.success("✅ Travel Plan Added!")
        st.rerun()

    st.subheader("All Travel Plans")
    for t in get_travel_plans():
        st.markdown(f"✈️ **{t['traveller']}** — {t['from_city']} → {t['to_city']} on {t['date']}  \n🎟️ [Ticket]({t['ticket_url']})")
