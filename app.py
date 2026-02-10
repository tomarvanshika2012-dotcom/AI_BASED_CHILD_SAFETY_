import streamlit as st
import sqlite3
import numpy as np
from datetime import datetime
from streamlit_geolocation import streamlit_geolocation
from twilio.rest import Client

# ================== SAFE OPENCV IMPORT ==================
try:
    import cv2
    CV2_AVAILABLE = True
except Exception:
    CV2_AVAILABLE = False

# ================== PAGE CONFIG ==================
st.set_page_config(
    page_title="AI Child Safety System",
    page_icon="🛡️",
    layout="centered"
)
st.title("🛡️ AI Child Safety System")

if not CV2_AVAILABLE:
    st.warning(
        "⚠️ Camera-based AI is limited in this environment.\n"
        "Image upload is available."
    )

# ================== DATABASE ==================
DB_FILE = "child_safety.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS children (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        age INTEGER,
        photo BLOB,
        face BLOB,
        clothing_color TEXT,
        lost_location TEXT,
        registered_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS sos_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        latitude REAL,
        longitude REAL,
        time TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ================== AI FUNCTIONS ==================
if CV2_AVAILABLE:
    FACE_CASCADE = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
else:
    FACE_CASCADE = None

def extract_face(image):
    if not CV2_AVAILABLE or FACE_CASCADE is None:
        return None
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = FACE_CASCADE.detectMultiScale(gray, 1.3, 5)
    if len(faces) == 0:
        return None
    x, y, w, h = faces[0]
    return cv2.resize(gray[y:y+h, x:x+w], (200, 200))

def compare_faces(f1, f2):
    error = np.mean((f1.astype("float") - f2.astype("float")) ** 2)
    return error < 4000

# ================== TWILIO CONFIG ==================
TWILIO_ACCOUNTS = [
    {
        "sid": "ACc9b9941c778de30e2ed7ba57f87cdfbc",
        "token": "447ac1385fd300bff05d08380e4a2bd4",
        "phone": "+15075195618"
    },
    {
        "sid": "ACa12e602647785572ebaf765659d26d23",
        "token": "206ca9f819c0ce34b6a96f6958531262",
        "phone": "+14176076960"
    }
]

EMERGENCY_CONTACTS = [
    "+917678495189",
    "+918130631551"
]

def send_sos_alert(lat, lon):
    msg = (
        "🚨 CHILD SAFETY SOS 🚨\n"
        f"Location: https://www.google.com/maps?q={lat},{lon}"
    )
    voice = (
        "Emergency alert. A child safety SOS has been triggered. "
        "Please check the location immediately."
    )

    success = False

    for acc in TWILIO_ACCOUNTS:
        client = Client(acc["sid"], acc["token"])

        for num in EMERGENCY_CONTACTS:
            try:
                client.messages.create(
                    body=msg,
                    from_=acc["phone"],
                    to=num
                )
                client.calls.create(
                    twiml=f"<Response><Say>{voice}</Say></Response>",
                    from_=acc["phone"],
                    to=num
                )
                st.success(f"✅ SOS sent from {acc['phone']} → {num}")
                success = True
            except Exception as e:
                st.warning(f"❌ Failed from {acc['phone']} → {num}: {e}")

    return success

# ================== UI TABS ==================
tab1, tab2, tab3 = st.tabs(
    ["📝 Register Child", "🔍 Face Match (Camera / Upload)", "🚨 Emergency SOS"]
)

# ================== TAB 1: REGISTER ==================
with tab1:
    st.header("Register Child")

    with st.form("register"):
        name = st.text_input("Child Name")
        age = st.number_input("Age", 1, 18)
        clothing = st.text_input("Clothing Color")
        lost_loc = st.text_input("Last Seen Location")
        photo = st.file_uploader("Upload Recent Photo", ["jpg", "png", "jpeg"])

        if st.form_submit_button("Register Child"):
            if name and photo:
                img_bytes = photo.read()
                face_bytes = None

                if CV2_AVAILABLE:
                    img = cv2.imdecode(
                        np.frombuffer(img_bytes, np.uint8),
                        cv2.IMREAD_COLOR
                    )
                    face = extract_face(img)
                    if face is not None:
                        face_bytes = face.tobytes()

                conn = sqlite3.connect(DB_FILE)
                conn.execute("""
                    INSERT INTO children
                    (name, age, photo, face, clothing_color, lost_location, registered_at)
                    VALUES (?,?,?,?,?,?,?)
                """, (
                    name, age, img_bytes, face_bytes,
                    clothing, lost_loc,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
                conn.commit()
                conn.close()

                st.success("✅ Child registered successfully")
            else:
                st.warning("⚠️ Name and photo required")

# ================== TAB 2: FACE MATCH (BROWSER + UPLOAD) ==================
with tab2:
    st.header("🔍 Face Verification")

    conn = sqlite3.connect(DB_FILE)
    row = conn.execute(
        "SELECT name, face FROM children ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()

    if not row or row[1] is None:
        st.warning("No registered face available.")
    else:
        stored_name, stored_face = row
        stored_face = np.frombuffer(
            stored_face, dtype=np.uint8
        ).reshape((200, 200))

        st.info(f"Registered Child: **{stored_name}**")

        mode = st.radio(
            "Choose input method",
            ["📷 Browser Camera", "📁 Upload Image"]
        )

        input_bytes = None

        if mode == "📷 Browser Camera":
            cam = st.camera_input("Capture using browser camera")
            if cam:
                input_bytes = cam.read()
        else:
            uploaded = st.file_uploader(
                "Upload image for verification",
                ["jpg", "png", "jpeg"]
            )
            if uploaded:
                input_bytes = uploaded.read()

        if input_bytes and CV2_AVAILABLE:
            img = cv2.imdecode(
                np.frombuffer(input_bytes, np.uint8),
                cv2.IMREAD_COLOR
            )
            face = extract_face(img)

            if face is None:
                st.error("❌ No face detected")
            elif compare_faces(stored_face, face):
                st.success("✅ MATCH FOUND")
                st.balloons()
            else:
                st.error("❌ NO MATCH")

# ================== TAB 3: SOS ==================
with tab3:
    st.header("🚨 Emergency SOS")

    location = streamlit_geolocation()

    if st.button("🚨 ACTIVATE SOS"):
        if location.get("latitude"):
            lat, lon = location["latitude"], location["longitude"]

            conn = sqlite3.connect(DB_FILE)
            conn.execute(
                "INSERT INTO sos_logs (latitude, longitude, time) VALUES (?,?,?)",
                (lat, lon, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            conn.commit()
            conn.close()

            sent = send_sos_alert(lat, lon)
            if sent:
                st.error("🚨 SOS SENT SUCCESSFULLY")
            else:
                st.error("❌ SOS FAILED")
        else:
            st.warning("Location permission not granted")

# ================== SOS LOGS ==================
st.subheader("📂 Recent SOS Logs")

conn = sqlite3.connect(DB_FILE)
logs = conn.execute(
    "SELECT latitude, longitude, time FROM sos_logs ORDER BY id DESC LIMIT 5"
).fetchall()
conn.close()

for log in logs:
    st.write(f"📍 {log[0]}, {log[1]} | ⏰ {log[2]}")
