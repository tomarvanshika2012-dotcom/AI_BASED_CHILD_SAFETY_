import streamlit as st
import sqlite3
import cv2
import numpy as np
from datetime import datetime
from twilio.rest import Client
from streamlit_geolocation import streamlit_geolocation

# =========================
# TWILIO CONFIG
# =========================

TWILIO_SID = "ACc9b9941c778de30e2ed7ba57f87cdfbc"
TWILIO_AUTH_TOKEN = "b524116dc4b14af314a5919594df9121"
TWILIO_PHONE = "+15075195618"
REGISTERED_PHONE = "+918130631551"

DB_FILE = "child_safety.db"

FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

st.set_page_config(
    page_title="SafeGuard AI Child Safety",
    page_icon="🛡️",
    layout="centered"
)

# =========================
# SOS BUTTON STYLE (BIGGER)
# =========================

st.markdown("""
<style>
.sos-btn button {
    background-color: #ff2b2b;
    color: white;
    height: 260px;
    width: 260px;
    border-radius: 50%;
    font-size: 44px;
    font-weight: bold;
    border: 12px solid #b30000;
    box-shadow: 0px 15px 35px rgba(255, 0, 0, 0.45);
    transition: all 0.2s ease-in-out;
}
.sos-btn button:hover {
    transform: scale(1.05);
}
.sos-btn button:active {
    transform: scale(0.95);
}
</style>
""", unsafe_allow_html=True)

# =========================
# DATABASE
# =========================

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS child (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            age INTEGER,
            clothing_color TEXT,
            lost_location TEXT,
            photo BLOB,
            face_encoding BLOB,
            registered_at TEXT
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
# FACE FUNCTIONS
# =========================

def extract_face(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = FACE_CASCADE.detectMultiScale(gray, 1.3, 5)
    if len(faces) == 0:
        return None
    x, y, w, h = faces[0]
    return cv2.resize(gray[y:y+h, x:x+w], (200, 200))

def compare_faces(f1, f2):
    if f1 is None or f2 is None:
        return False
    diff = np.mean(cv2.absdiff(f1, f2))
    return diff < 60

# =========================
# SOS FUNCTION
# =========================

def send_sos(lat, lon, lang):
    client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

    now = datetime.now().strftime("%d-%m-%Y %I:%M %p")
    maps = f"https://www.google.com/maps?q={lat},{lon}"

    client.messages.create(
        body=f"🚨 CHILD SOS ALERT 🚨\nTime: {now}\nLocation: {maps}",
        from_=TWILIO_PHONE,
        to=REGISTERED_PHONE
    )

    speech = (
        "Emergency alert. Your child has triggered the SOS system."
        if lang == "English"
        else "आपातकालीन अलर्ट। आपके बच्चे ने SOS सिस्टम सक्रिय किया है।"
    )

    client.calls.create(
        twiml=f"<Response><Say>{speech}</Say></Response>",
        from_=TWILIO_PHONE,
        to=REGISTERED_PHONE
    )

    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "INSERT INTO sos_log(latitude, longitude, time) VALUES (?,?,?)",
        (lat, lon, now)
    )
    conn.commit()
    conn.close()

# =========================
# UI
# =========================

st.title("🛡️ SafeGuard AI Child Safety System")

tab1, tab2, tab3 = st.tabs([
    "📝 Child Registration",
    "📸 Face Verification",
    "🆘 Emergency SOS"
])

# --------------------------------------------------
# REGISTRATION
# --------------------------------------------------

with tab1:
    st.subheader("Parent Registration")

    name = st.text_input("Child Name")
    age = st.number_input("Child Age", 1, 18)
    clothing = st.text_input("Clothing Color")
    lost_location = st.text_input("Lost Location")
    photo = st.file_uploader("Upload Child Photo", type=["jpg", "png", "jpeg"])

    if st.button("Register Child"):
        if not all([name, age, clothing, lost_location, photo]):
            st.error("All fields required")
        else:
            img_bytes = photo.read()
            img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
            face = extract_face(img)

            if face is None:
                st.error("No face detected")
            else:
                conn = sqlite3.connect(DB_FILE)
                conn.execute("""
                    INSERT INTO child
                    (name, age, clothing_color, lost_location, photo, face_encoding, registered_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    name,
                    age,
                    clothing,
                    lost_location,
                    img_bytes,
                    face.tobytes(),
                    datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                ))
                conn.commit()
                conn.close()

                st.success("✅ Child registered successfully")

# --------------------------------------------------
# FACE VERIFICATION
# --------------------------------------------------

with tab2:
    st.subheader("Face Verification")

    mode = st.radio("Mode", ["Live Camera", "Upload Image"])

    conn = sqlite3.connect(DB_FILE)
    row = conn.execute(
        "SELECT face_encoding FROM child ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()

    stored_face = None
    if row:
        stored_face = np.frombuffer(row[0], dtype=np.uint8).reshape((200, 200))

    if mode == "Live Camera":
        cam = st.camera_input("Capture")
        if cam:
            img = cv2.imdecode(np.frombuffer(cam.read(), np.uint8), cv2.IMREAD_COLOR)
            face = extract_face(img)
            st.success("✅ Match Found") if compare_faces(stored_face, face) else st.error("❌ No Match")

    else:
        img = st.file_uploader("Upload Image", type=["jpg", "png"])
        if img:
            img = cv2.imdecode(np.frombuffer(img.read(), np.uint8), cv2.IMREAD_COLOR)
            face = extract_face(img)
            st.success("✅ Match Found") if compare_faces(stored_face, face) else st.error("❌ No Match")

# --------------------------------------------------
# SOS (BIGGER BUTTON)
# --------------------------------------------------

with tab3:
    st.subheader("Emergency SOS")

    lang = st.radio("Call Language", ["English", "Hindi"])
    location = streamlit_geolocation()

    st.markdown('<div class="sos-btn">', unsafe_allow_html=True)
    sos_pressed = st.button("🆘")
    st.markdown('</div>', unsafe_allow_html=True)

    if sos_pressed:
        if location["latitude"]:
            send_sos(location["latitude"], location["longitude"], lang)
            st.success("🚨 SOS sent successfully")
            st.balloons()
        else:
            st.error("Location permission denied")

    if location["latitude"]:
        st.markdown(
            f"[📍 View Location](https://www.google.com/maps?q={location['latitude']},{location['longitude']})"
        )
