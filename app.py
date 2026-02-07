import streamlit as st
import sqlite3
import cv2
import numpy as np
import tempfile
import os
from datetime import datetime
from twilio.rest import Client
from streamlit_geolocation import streamlit_geolocation

# =========================
# 1. CONFIGURATION
# =========================

TWILIO_SID = "ACa12e602647785572ebaf765659d26d23"
TWILIO_AUTH_TOKEN = "0e150a10a98b74ddc7d57e44fa3e01c6"
TWILIO_PHONE = "+14176076960"
REGISTERED_PHONE = "+918130631551"

DB_FILE = "child_safety.db"
FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

st.set_page_config(page_title="SafeGuard AI Child Safety", page_icon="🛡️", layout="centered")

# =========================
# 2. DATABASE
# =========================

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS child (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS sos_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            latitude REAL,
            longitude REAL,
            time TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# =========================
# 3. STYLES
# =========================

st.markdown("""
<style>
.sos-btn button {
    background-color:#ff4b4b;
    color:white;
    height:220px;
    width:220px;
    border-radius:50%;
    font-size:38px;
    border:10px solid #b30000;
}
</style>
""", unsafe_allow_html=True)

# =========================
# 4. FACE UTILITIES
# =========================

def extract_face(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = FACE_CASCADE.detectMultiScale(gray, 1.3, 5)
    if len(faces) == 0:
        return None
    x, y, w, h = faces[0]
    return cv2.resize(gray[y:y+h, x:x+w], (200, 200))

def compare_faces(face1, face2):
    if face1 is None or face2 is None:
        return False
    diff = np.mean(cv2.absdiff(face1, face2))
    return diff < 60   # tolerance for low quality images

# =========================
# 5. SOS FUNCTION
# =========================

def send_sos(lat, lon, lang):
    client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
    now = datetime.now().strftime("%d-%m-%Y %I:%M %p")
    maps = f"https://www.google.com/maps?q={lat},{lon}"

    client.messages.create(
        body=f"🚨 CHILD SOS 🚨\nTime: {now}\nLocation: {maps}",
        from_=TWILIO_PHONE,
        to=REGISTERED_PHONE
    )

    msg = (
        "Emergency alert! Your child pressed the SOS button."
        if lang == "English"
        else "आपातकालीन अलर्ट। आपके बच्चे ने SOS बटन दबाया है।"
    )

    client.calls.create(
        twiml=f"<Response><Say>{msg}</Say></Response>",
        from_=TWILIO_PHONE,
        to=REGISTERED_PHONE
    )

    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT INTO sos_log(latitude, longitude, time) VALUES (?,?,?)",
                 (lat, lon, now))
    conn.commit()
    conn.close()

# =========================
# 6. UI
# =========================

st.title("🛡️ SafeGuard AI Child Safety System")

tab1, tab2, tab3 = st.tabs(["🧠 Face Recognition", "📸 Camera / Upload", "🆘 SOS"])

# -------- TAB 1: REGISTER FACE --------
with tab1:
    st.subheader("Register Child Face")
    child_name = st.text_input("Child Name")
    img = st.file_uploader("Upload Child Image", type=["jpg", "png", "jpeg"])

    if img and st.button("Save Face"):
        img_np = np.frombuffer(img.read(), np.uint8)
        image = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
        face = extract_face(image)

        if face is None:
            st.error("No face detected.")
        else:
            np.save("child_face.npy", face)
            conn = sqlite3.connect(DB_FILE)
            conn.execute("INSERT INTO child(name, created_at) VALUES (?,?)",
                         (child_name, datetime.now()))
            conn.commit()
            conn.close()
            st.success("Face Registered Successfully")

# -------- TAB 2: LIVE CAMERA / UPLOAD --------
with tab2:
    st.subheader("Verify Face")

    option = st.radio("Select Mode", ["Live Camera", "Upload Image"])

    if os.path.exists("child_face.npy"):
        stored_face = np.load("child_face.npy")
    else:
        stored_face = None

    if option == "Live Camera":
        cam = st.camera_input("Capture Image")
        if cam:
            img = cv2.imdecode(np.frombuffer(cam.read(), np.uint8), cv2.IMREAD_COLOR)
            face = extract_face(img)
            if compare_faces(stored_face, face):
                st.success("✅ Child Verified")
            else:
                st.error("❌ Face Not Matched")

    else:
        img = st.file_uploader("Upload Image", type=["jpg", "png"])
        if img:
            img = cv2.imdecode(np.frombuffer(img.read(), np.uint8), cv2.IMREAD_COLOR)
            face = extract_face(img)
            if compare_faces(stored_face, face):
                st.success("✅ Child Verified")
            else:
                st.error("❌ Face Not Matched")

# -------- TAB 3: SOS --------
with tab3:
    st.subheader("Emergency SOS")
    lang = st.radio("Call Language", ["English", "Hindi"])
    location = streamlit_geolocation()

    if st.button("🆘 SOS", key="sos"):
        if location["latitude"]:
            send_sos(location["latitude"], location["longitude"], lang)
            st.success("🚨 SOS Sent Successfully")
            st.balloons()
        else:
            st.error("Location access denied")

    if location["latitude"]:
        st.write("📍 Location:",
                 location["latitude"], location["longitude"])
        st.markdown(
            f"[View on Map](https://www.google.com/maps?q={location['latitude']},{location['longitude']})"
        )
