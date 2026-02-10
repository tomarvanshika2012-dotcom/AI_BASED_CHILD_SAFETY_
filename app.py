import streamlit as st
import cv2
import numpy as np
import threading
import time
from datetime import datetime
from twilio.rest import Client
from streamlit_geolocation import streamlit_geolocation

# ===== MongoDB =====
from pymongo import MongoClient
from bson.binary import Binary

# ==================================================
# 1. CONFIGURATION
# ==================================================
TWILIO_SID = "ACc9b9941c778de30e2ed7ba57f87cdfbc"
TWILIO_AUTH_TOKEN = "2b2cf2200be3a515c496ffd9137d63c4"

TWILIO_PHONE_NUMBER = "+15075195618"
TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"

EMERGENCY_CONTACTS = [
    "+918130631551",
    "+917678495189"
]

# ===== MongoDB Connection =====
MONGO_URI = "mongodb+srv://USERNAME:PASSWORD@cluster0.mongodb.net/"
client = MongoClient(MONGO_URI)

db = client["child_safety_db"]
children_col = db["children"]
sos_col = db["sos_logs"]

# ===== Face Cascade =====
FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

st.set_page_config(page_title="SafeGuard AI", page_icon="🛡️", layout="centered")

# ==================================================
# 2. HELPER FUNCTIONS
# ==================================================
def extract_face(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = FACE_CASCADE.detectMultiScale(gray, 1.3, 5)
    if len(faces) == 0:
        return None
    x, y, w, h = faces[0]
    return cv2.resize(gray[y:y+h, x:x+w], (200, 200))

def compare_faces(f1, f2):
    err = np.sum((f1.astype("float") - f2.astype("float")) ** 2)
    err /= float(f1.shape[0] * f1.shape[1])
    return err < 4000

# ==================================================
# 3. ALERT SYSTEM
# ==================================================
def send_alert_thread(contact, msg_body, speech, lang_code, log_container):
    client_twilio = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
    status = {}

    try:
        client_twilio.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=f"whatsapp:{contact}",
            body=msg_body
        )
        status["WhatsApp"] = "✅ Sent"
    except Exception as e:
        status["WhatsApp"] = f"❌ {e}"

    try:
        client_twilio.messages.create(
            from_=TWILIO_PHONE_NUMBER,
            to=contact,
            body=msg_body
        )
        status["SMS"] = "✅ Sent"
    except Exception as e:
        status["SMS"] = f"❌ {e}"

    try:
        client_twilio.calls.create(
            from_=TWILIO_PHONE_NUMBER,
            to=contact,
            twiml=f'<Response><Say language="{lang_code}">{speech}</Say></Response>'
        )
        status["Call"] = "✅ Initiated"
    except Exception as e:
        status["Call"] = f"❌ {e}"

    log_container[contact] = status

def trigger_sos(lat, lon, language):
    timestamp = datetime.now().strftime("%d-%m-%Y %I:%M %p")
    maps_link = f"https://www.google.com/maps?q={lat},{lon}"

    child = children_col.find_one(sort=[("registered_at", -1)])
    name = child["name"] if child else "Unknown Child"

    msg_body = (
        f"🚨 SOS ALERT 🚨\n"
        f"Child: {name}\n"
        f"📍 Location: {maps_link}\n"
        f"⏰ Time: {timestamp}"
    )

    if language == "Hindi":
        speech = f"Aapaatkaaleen alert. {name} ko madad chahiye."
        lang_code = "hi-IN"
    else:
        speech = f"Emergency alert. {name} needs immediate help."
        lang_code = "en-US"

    logs = {}
    threads = []

    for contact in EMERGENCY_CONTACTS:
        t = threading.Thread(
            target=send_alert_thread,
            args=(contact, msg_body, speech, lang_code, logs)
        )
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    sos_col.insert_one({
        "latitude": lat,
        "longitude": lon,
        "time": timestamp,
        "status": "Triggered"
    })

    return logs

# ==================================================
# 4. STREAMLIT UI
# ==================================================
st.title("🛡️ SafeGuard AI")

tab1, tab2, tab3 = st.tabs(["📝 Registration", "🔍 Face Match", "🆘 SOS"])

# ---------- REGISTRATION ----------
with tab1:
    with st.form("reg"):
        name = st.text_input("Child Name")
        age = st.number_input("Age", 1, 18)
        clothes = st.text_input("Clothing Color")
        photo = st.file_uploader("Upload Photo", ["jpg", "png"])

        if st.form_submit_button("Register"):
            if photo and name:
                img = cv2.imdecode(np.frombuffer(photo.read(), np.uint8), cv2.IMREAD_COLOR)
                face = extract_face(img)

                if face is not None:
                    children_col.insert_one({
                        "name": name,
                        "age": age,
                        "clothing": clothes,
                        "photo": Binary(photo.read()),
                        "face": Binary(face.tobytes()),
                        "registered_at": datetime.now()
                    })
                    st.success("✅ Child Registered")
                else:
                    st.error("❌ No face detected")

# ---------- FACE MATCH ----------
with tab2:
    child = children_col.find_one(sort=[("registered_at", -1)])
    if child:
        target_face = np.frombuffer(child["face"], dtype=np.uint8).reshape((200, 200))
        cam = st.camera_input("Scan Face")

        if cam:
            img = cv2.imdecode(np.frombuffer(cam.read(), np.uint8), cv2.IMREAD_COLOR)
            face = extract_face(img)
            if face is not None and compare_faces(target_face, face):
                st.success("✅ MATCH FOUND")
            else:
                st.error("❌ NO MATCH")

# ---------- SOS ----------
with tab3:
    language = st.selectbox("Voice Language", ["English", "Hindi"])
    location = streamlit_geolocation()

    if st.button("🆘 ACTIVATE SOS"):
        if location.get("latitude"):
            logs = trigger_sos(
                location["latitude"],
                location["longitude"],
                language
            )
            st.success("SOS Sent!")
            st.json(logs)
        else:
            st.error("Location not available")
