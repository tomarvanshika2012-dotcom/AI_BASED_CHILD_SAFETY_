import streamlit as st
import sqlite3
import os
import uuid
import threading
from PIL import Image
from datetime import datetime
from twilio.rest import Client
from streamlit_geolocation import streamlit_geolocation
import cv2
import numpy as np

# ================== APP CONFIG ==================
st.set_page_config(
    page_title="SafeGuard Child Safety AI",
    page_icon="🛡️",
    layout="centered"
)

UPLOAD_DIR = "uploads"
DB_FILE = "child_safety.db"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ================== TWILIO (TWO ACCOUNTS) ==================

# Twilio Account 1
TWILIO1_SID = "ACa12e602647785572ebaf765659d26d23"
TWILIO1_AUTH = "0e150a10a98b74ddc7d57e44fa3e01c6"
TWILIO1_PHONE = "+14176076960"

# Twilio Account 2
TWILIO2_SID = "ACc9b9941c778de30e2ed7ba57f87cdfbc"
TWILIO2_AUTH = "b524116dc4b14af314a5919594df9121"
TWILIO2_PHONE = "+15075195618"

# Emergency receivers
EMERGENCY_CONTACTS = [
    "+918130631551",
    "+917678495189"
]

# ================== DATABASE ==================
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS child_registry (
    id TEXT PRIMARY KEY,
    child_name TEXT,
    age INTEGER,
    clothing_color TEXT,
    lost_location TEXT,
    image_path TEXT,
    created_at TEXT
)
""")
conn.commit()

# ================== SIDEBAR ==================
with st.sidebar:
    st.header("🚨 Emergency Network")
    st.success(f"{len(EMERGENCY_CONTACTS)} Contacts Linked")
    voice_lang = st.radio("Call Language", ["English", "Hindi"])

# ================== FACE DETECTION ==================
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

def extract_face(gray):
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    if len(faces) == 0:
        return None
    x, y, w, h = faces[0]
    return cv2.resize(gray[y:y+h, x:x+w], (200, 200))

def match_faces(stored_path, test_np):
    stored_img = cv2.imread(stored_path)
    if stored_img is None:
        return False, "Stored image missing"

    gray1 = cv2.cvtColor(stored_img, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(test_np, cv2.COLOR_RGB2GRAY)

    f1 = extract_face(gray1)
    f2 = extract_face(gray2)

    if f1 is None or f2 is None:
        return False, "Face not detected"

    diff = np.mean(np.abs(f1 - f2))
    if diff < 40:
        return True, f"Match Found (Score: {diff:.2f})"
    return False, f"No Match (Score: {diff:.2f})"

# ================== HELPERS ==================
def get_latest_child():
    cursor.execute("""
        SELECT child_name, age, clothing_color, lost_location, image_path
        FROM child_registry
        ORDER BY created_at DESC LIMIT 1
    """)
    return cursor.fetchone()

def send_alert(client, from_phone, to_phone, msg, speech, lang):
    try:
        client.messages.create(
            body=msg,
            from_=from_phone,
            to=to_phone
        )

        client.calls.create(
            twiml=f'<Response><Say language="{lang}">{speech}</Say></Response>',
            from_=from_phone,
            to=to_phone
        )
    except Exception as e:
        print(f"Twilio error {from_phone} → {to_phone}: {e}")

def trigger_emergency(lat, lon, lang_choice):
    child = get_latest_child()
    if not child:
        return "No child registered"

    name, age, clothes, last_loc, _ = child
    time_now = datetime.now().strftime("%d-%m-%Y | %I:%M %p")
    maps = f"https://www.google.com/maps?q={lat},{lon}"

    msg = (
        f"🚨 CHILD SAFETY ALERT 🚨\n"
        f"Name: {name}\nAge: {age}\n"
        f"Clothes: {clothes}\n"
        f"Last Seen: {last_loc}\n"
        f"Location: {maps}\n"
        f"Time: {time_now}"
    )

    if lang_choice == "English":
        speech = f"Emergency alert. {name} has triggered SOS. Location has been sent."
        lang = "en-US"
    else:
        speech = f"आपातकालीन अलर्ट। {name} ने एस ओ एस भेजा है।"
        lang = "hi-IN"

    client1 = Client(TWILIO1_SID, TWILIO1_AUTH)
    client2 = Client(TWILIO2_SID, TWILIO2_AUTH)

    threads = []

    for contact in EMERGENCY_CONTACTS:
        t1 = threading.Thread(
            target=send_alert,
            args=(client1, TWILIO1_PHONE, contact, msg, speech, lang)
        )
        t2 = threading.Thread(
            target=send_alert,
            args=(client2, TWILIO2_PHONE, contact, msg, speech, lang)
        )

        threads.extend([t1, t2])
        t1.start()
        t2.start()

    for t in threads:
        t.join()

    return True

# ================== UI ==================
st.title("🛡️ SafeGuard Child Safety AI")

tab1, tab2, tab3 = st.tabs([
    "👨‍👩‍👧 Register Child",
    "🆘 SOS Emergency",
    "🧠 AI Face Matching"
])

# ================== TAB 1 ==================
with tab1:
    with st.form("register"):
        name = st.text_input("Child Name")
        age = st.number_input("Age", 0, 18)
        clothes = st.text_input("Clothing Color")
        last_loc = st.text_area("Last Seen Location")
        photo = st.file_uploader("Upload Photo", ["jpg", "png", "jpeg"])
        submit = st.form_submit_button("Register")

    if submit:
        if not all([name, clothes, last_loc, photo]):
            st.error("All fields are required")
        else:
            cid = str(uuid.uuid4())
            img = Image.open(photo).convert("RGB")
            path = os.path.join(UPLOAD_DIR, f"{cid}.jpg")
            img.save(path)

            cursor.execute(
                "INSERT INTO child_registry VALUES (?, ?, ?, ?, ?, ?, ?)",
                (cid, name, age, clothes, last_loc, path, datetime.now().isoformat())
            )
            conn.commit()

            st.success("Child Registered Successfully")
            st.image(img, width=200)

# ================== TAB 2 ==================
with tab2:
    st.warning("SOS will send SMS + CALL from BOTH Twilio numbers.")
    location = streamlit_geolocation() or {}

    if st.button("🆘 TRIGGER SOS"):
        if location.get("latitude") and location.get("longitude"):
            with st.spinner("Sending emergency alerts..."):
                result = trigger_emergency(
                    location["latitude"],
                    location["longitude"],
                    voice_lang
                )
            if result is True:
                st.success("SMS & Calls sent successfully")
                st.balloons()
            else:
                st.error(result)
        else:
            st.error("Please allow location access")

# ================== TAB 3 ==================
with tab3:
    mode = st.radio("Image Source", ["📷 Camera", "🖼️ Upload"])
    test_np = None

    if mode == "📷 Camera":
        cam = st.camera_input("Capture Image")
        if cam:
            test_np = np.array(Image.open(cam).convert("RGB"))

    if mode == "🖼️ Upload":
        up = st.file_uploader("Upload Image", ["jpg", "png", "jpeg"])
        if up:
            test_np = np.array(Image.open(up).convert("RGB"))

    if test_np is not None:
        child = get_latest_child()
        if child:
            _, _, _, _, stored_path = child
            ok, msg = match_faces(stored_path, test_np)
            if ok:
                st.success(msg)
                st.balloons()
            else:
                st.error(msg)
        else:
            st.warning("No child registered yet")
