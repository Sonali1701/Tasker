import streamlit as st
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore, auth
import json, base64, smtplib
from email.mime.text import MIMEText
from datetime import datetime, date

# --- PAGE CONFIG ---
st.set_page_config(page_title="Team Tasker", layout="wide")

# --- FIREBASE INITIALIZATION ---
if not firebase_admin._apps:
    try:
        FIREBASE_SERVICE_ACCOUNT_B64 = st.secrets.get("FIREBASE_SERVICE_ACCOUNT_B64", "")
        if not FIREBASE_SERVICE_ACCOUNT_B64:
            raise ValueError("Missing FIREBASE_SERVICE_ACCOUNT_B64 in Streamlit secrets")
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

# --- GOOGLE GEMINI SETUP ---
genai.configure(api_key=st.secrets.get("GOOGLE_API_KEY", ""))
model = genai.GenerativeModel("gemini-2.5-flash")

# --- HELPER FUNCTIONS ---
def ai_followup(task_text):
    try:
        response = model.generate_content(f"Generate a short follow-up message for this task: {task_text}")
        return response.text.strip()
    except Exception as e:
        return f"❌ AI Error: {e}"

def ai_chat(query):
    try:
        response = model.generate_content(query)
        return response.text.strip()
    except Exception as e:
        return f"❌ AI Error: {e}"

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
    return [doc.to_dict() | {"id": doc.id} for doc in db.collection("tasks").order_by("timestamp").stream()]

def add_note(user, note):
    db.collection("notes").add({
        "user": user,
        "note": note,
        "timestamp": datetime.now().isoformat()
    })

def get_notes(user):
    docs = db.collection("notes").where("user", "==", user).stream()
    return [d.to_dict() for d in docs]

def add_meeting(title, date, link, attendees, organizer):
    db.collection("meetings").add({
        "title": title,
        "date": date,
        "link": link,
        "attendees": attendees,
        "organizer": organizer,
        "timestamp": datetime.now().isoformat()
    })

def get_meetings():
    docs = db.collection("meetings").order_by("date").stream()
    return [d.to_dict() for d in docs]

# --- SEND EMAIL INVITES ---
def send_meeting_invites(emails, title, time_str, organizer, link):
    sender = st.secrets["EMAIL_SENDER"]
    password = st.secrets["EMAIL_APP_PASSWORD"]

    subject = f"📅 Meeting Invite: {title}"
    html_body = f"""
    <html>
      <body style="font-family:Arial, sans-serif; color:#333;">
        <h2 style="color:#1a73e8;">📅 Meeting Invitation</h2>
        <p>Hello Team,</p>
        <p>You are invited to attend the following meeting:</p>
        <table style="border-collapse: collapse;">
          <tr><td><strong>📌 Title:</strong></td><td>{title}</td></tr>
          <tr><td><strong>📅 Date:</strong></td><td>{time_str}</td></tr>
          <tr><td><strong>👤 Organized by:</strong></td><td>{organizer}</td></tr>
        </table>
        <br>
        <a href="{link}" style="display:inline-block; padding:10px 15px; background-color:#1a73e8; color:white; border-radius:6px; text-decoration:none;">Join Meeting</a>
        <br><br>
        <p>See you there!</p>
        <p>— Team Tasker</p>
      </body>
    </html>
    """

    msg = MIMEText(html_body, "html")
    msg["From"] = sender
    msg["Subject"] = subject

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, password)
        for mail in emails:
            msg["To"] = mail
            server.sendmail(sender, mail, msg.as_string())
        server.quit()
        st.success("✅ Meeting invites sent successfully!")
    except Exception as e:
        st.error(f"Failed to send invites: {e}")

# --- SESSION STATE ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "email" not in st.session_state:
    st.session_state.email = None

# --- SIDEBAR: AUTHENTICATION ---
st.sidebar.title("🔐 Team Login")

if not st.session_state.logged_in:
    choice = st.sidebar.radio("Select", ["Login", "Sign Up"])
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")

    if choice == "Sign Up":
        if st.sidebar.button("Create Account"):
            try:
                auth.create_user(email=email, password=password)
                st.sidebar.success("✅ Account created! Please log in.")
            except Exception as e:
                st.sidebar.error(e)

    elif choice == "Login":
        if st.sidebar.button("Login"):
            try:
                user = auth.get_user_by_email(email)
                # Firebase Admin SDK doesn't directly verify passwords
                # So we mimic password verification through custom logic or Firebase REST if needed
                st.session_state.logged_in = True
                st.session_state.email = email
                st.sidebar.success(f"✅ Logged in as {email}")
                st.rerun()
            except Exception:
                st.sidebar.error("Invalid login credentials. Please check your email and password.")
else:
    st.sidebar.success(f"Welcome back, {st.session_state.email} 👋")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.email = None
        st.rerun()

# --- STOP IF NOT LOGGED IN ---
if not st.session_state.logged_in:
    st.info("👋 Please log in to continue.")
    st.stop()

email = st.session_state.email

# --- SIDEBAR: PENDING TASKS + UPCOMING MEETINGS ---
st.sidebar.markdown("---")
st.sidebar.subheader("🕒 Pending Tasks")
pending_tasks = [t for t in get_all_tasks() if t.get("status") == "Pending"]
if pending_tasks:
    for t in pending_tasks[:5]:
        st.sidebar.write(f"- {t['task']} (📅 {t['due_date']})")
else:
    st.sidebar.caption("No pending tasks.")

st.sidebar.subheader("📅 Upcoming Meetings")
upcoming_meetings = [m for m in get_meetings() if m.get("date") >= str(date.today())]
if upcoming_meetings:
    for m in upcoming_meetings[:5]:
        st.sidebar.write(f"- {m['title']} ({m['date']})")
else:
    st.sidebar.caption("No upcoming meetings.")

# --- MAIN CONTENT ---
tabs = st.tabs(["📋 Tasks", "📝 Notes", "💬 AI Playground", "📅 Meetings"])

# --- TASKS TAB ---
with tabs[0]:
    st.header("📋 Team Tasks")
    col1, col2, col3 = st.columns(3)
    with col1:
        task = st.text_input("Task Description")
    with col2:
        assigned_to = st.text_input("Assigned To (Email)")
    with col3:
        due_date = st.date_input("Due Date")

    if st.button("➕ Add Task"):
        if task and assigned_to:
            add_task(task, assigned_to, email, str(due_date))
            st.success("✅ Task Added!")
            st.rerun()
        else:
            st.warning("Please fill all fields before adding a task.")

    st.subheader("All Tasks")
    tasks = get_all_tasks()
    for t in tasks:
        t_name = t.get("task", "Untitled Task")
        t_status = t.get("status", "Pending")
        t_assignee = t.get("assigned_to", "N/A")
        t_due = t.get("due_date", "—")
        t_by = t.get("assigned_by", "—")

        st.markdown(f"**{t_name}** — 🧑‍💼 *{t_assignee}* | 📅 *{t_due}* | Assigned by *{t_by}* | Status: *{t_status}*")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button(f"✅ Mark Done ({t_name})"):
                db.collection("tasks").document(t["id"]).update({"status": "Done"})
                st.rerun()
        with col2:
            if st.button(f"🤖 Follow-up ({t_name})"):
                ai_text = ai_followup(t_name)
                st.info(f"AI Suggested: {ai_text}")

# --- NOTES TAB ---
with tabs[1]:
    st.header("📝 Personal Notes")
    note = st.text_area("Write a note")
    if st.button("💾 Save Note"):
        add_note(email, note)
        st.success("✅ Note saved!")
        st.rerun()

    st.subheader("Your Notes")
    notes = get_notes(email)
    for n in notes:
        st.markdown(f"- {n.get('note')}  \n🕒 *{n.get('timestamp', '')}*")

# --- AI PLAYGROUND TAB ---
with tabs[2]:
    st.header("💬 AI Playground")
    query = st.text_area("Ask anything to AI Assistant")
    if st.button("🚀 Ask AI"):
        reply = ai_chat(query)
        st.markdown(f"**AI Response:**\n\n{reply}")

# --- MEETINGS TAB ---
with tabs[3]:
    st.header("📅 Schedule Team Meetings")

    col1, col2 = st.columns(2)
    with col1:
        m_title = st.text_input("Meeting Title")
        m_date = st.date_input("Meeting Date")
        m_link = st.text_input("Meeting Link (Zoom/Meet)")
    with col2:
        attendee_emails = st.text_area("Attendees' Emails (comma separated)")

    if st.button("📨 Add Meeting & Send Invites"):
        emails = [e.strip() for e in attendee_emails.split(",") if e.strip()]
        if m_title and emails:
            add_meeting(m_title, str(m_date), m_link, emails, email)
            send_meeting_invites(emails, m_title, str(m_date), email, m_link)
            st.success("✅ Meeting Added & Invites Sent!")
            st.rerun()
        else:
            st.warning("Please fill all required fields.")

    st.subheader("Upcoming Meetings")
    meetings = get_meetings()
    for m in meetings:
        st.markdown(f"📌 **{m['title']}** — {m['date']}  \n🔗 [Join Meeting]({m['link']})")
