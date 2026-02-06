import streamlit as st
import sqlite3, os, uuid, threading
from PIL import Image
from datetime import datetime
from twilio.rest import Client
from streamlit_geolocation import streamlit_geolocation
import cv2, numpy as np

# ================== APP CONFIG ==================
st.set_page_config("SafeGuard Child Safety AI", "🛡️", layout="centered")

UPLOAD_DIR = "uploads"
DB_FILE = "child_safety.db"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ================== TWILIO CONFIG (2 ACCOUNTS) ==================
TWILIO1_SID = "ACa12e602647785572ebaf765659d26d23"
TWILIO1_AUTH = "0e150a10a98b74ddc7d57e44fa3e01c6"
TWILIO1_PHONE = "+14176076960"

TWILIO2_SID = "ACc9b9941c778de30e2ed7ba57f87cdfbc"
TWILIO2_AUTH = "b524116dc4b14af314a5919594df9121"
TWILIO2_PHONE = "+15075195618"

WHATSAPP_FROM = "whatsapp:+14155238886"  # Twilio sandbox

EMERGENCY_CONTACTS = [
    "+918130631551",
    "+91768495189"
]

# ================== DATABASE ==================
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cur = conn.cursor()
cur.execute("""
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

# ================== FACE AI ==================
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

def extract_face_from_path(path):
    img = cv2.imread(path)
    if img is None: return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    if len(faces) == 0: return None
    x,y,w,h = faces[0]
    return cv2.resize(gray[y:y+h, x:x+w], (200,200))

def extract_face_from_np(img_np):
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    if len(faces) == 0: return None
    x,y,w,h = faces[0]
    return cv2.resize(gray[y:y+h, x:x+w], (200,200))

def match_faces(stored_path, test_np):
    a = extract_face_from_path(stored_path)
    b = extract_face_from_np(test_np)
    if a is None or b is None:
        return False, "Face not detected"

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train([a], np.array([0]))
    _, conf = recognizer.predict(b)
    return (True, f"Match Found ({conf:.2f})") if conf < 75 else (False, f"No Match ({conf:.2f})")

# ================== HELPERS ==================
def get_latest_child():
    cur.execute("SELECT * FROM child_registry ORDER BY created_at DESC LIMIT 1")
    return cur.fetchone()

def send_alert(client, from_no, to_no, msg, speech, lang):
    try:
        # SMS
        client.messages.create(body=msg, from_=from_no, to=to_no)

        # WhatsApp
        client.messages.create(
            body=msg,
            from_=WHATSAPP_FROM,
            to=f"whatsapp:{to_no}"
        )

        # Call
        client.calls.create(
            twiml=f"""
            <Response>
                <Say voice="alice" language="{lang}">
                    {speech}
                </Say>
            </Response>
            """,
            from_=from_no,
            to=to_no
        )
    except Exception as e:
        print("TWILIO ERROR:", e)

def trigger_sos(lat, lon, lang_choice):
    child = get_latest_child()
    if not child:
        return "No child registered"

    _, name, age, clothes, last_loc, _, _ = child
    maps = f"https://www.google.com/maps?q={lat},{lon}"
    time_now = datetime.now().strftime("%d-%m-%Y %I:%M %p")

    msg = f"""🚨 CHILD SAFETY ALERT 🚨
Name: {name}
Age: {age}
Clothes: {clothes}
Last Seen: {last_loc}
📍 Location: {maps}
🕒 Time: {time_now}
"""

    if lang_choice == "English":
        speech, lang = f"Emergency alert. {name} needs immediate help.", "en-US"
    else:
        speech, lang = f"आपातकालीन चेतावनी। {name} को तुरंत मदद चाहिए।", "hi-IN"

    c1 = Client(TWILIO1_SID, TWILIO1_AUTH)
    c2 = Client(TWILIO2_SID, TWILIO2_AUTH)

    threads = []
    for n in EMERGENCY_CONTACTS:
        threads.append(threading.Thread(
            target=send_alert, args=(c1, TWILIO1_PHONE, n, msg, speech, lang)
        ))
        threads.append(threading.Thread(
            target=send_alert, args=(c2, TWILIO2_PHONE, n, msg, speech, lang)
        ))

    for t in threads: t.start()
    for t in threads: t.join()
    return True

# ================== UI ==================
st.title("🛡️ SafeGuard Child Safety AI")

tab1, tab2, tab3 = st.tabs([
    "👨‍👩‍👧 Register Child",
    "🆘 SOS Emergency",
    "🧠 AI Face Match"
])

with tab1:
    with st.form("reg"):
        name = st.text_input("Child Name")
        age = st.number_input("Age", 0, 18)
        clothes = st.text_input("Clothing Color")
        last_loc = st.text_area("Last Seen Location")
        photo = st.file_uploader("Photo", ["jpg","png","jpeg"])
        if st.form_submit_button("Register"):
            if all([name, clothes, last_loc, photo]):
                cid = str(uuid.uuid4())
                path = f"{UPLOAD_DIR}/{cid}.jpg"
                Image.open(photo).convert("RGB").save(path)
                cur.execute(
                    "INSERT INTO child_registry VALUES (?,?,?,?,?,?,?)",
                    (cid, name, age, clothes, last_loc, path, datetime.now().isoformat())
                )
                conn.commit()
                st.success("Child Registered")
            else:
                st.error("All fields required")

with tab2:
    voice_lang = st.radio("Call Language", ["English", "Hindi"])
    loc = streamlit_geolocation()
    if st.button("🆘 TRIGGER SOS"):
        if loc.get("latitude"):
            with st.spinner("Sending alerts..."):
                res = trigger_sos(loc["latitude"], loc["longitude"], voice_lang)
            st.success("SMS + Call + WhatsApp sent successfully") if res is True else st.error(res)
        else:
            st.error("Location permission required")

with tab3:
    src = st.radio("Image Source", ["Camera", "Upload"])
    img = None
    if src == "Camera":
        cam = st.camera_input("Capture")
        if cam: img = np.array(Image.open(cam))
    else:
        up = st.file_uploader("Upload Image", ["jpg","png","jpeg"])
        if up: img = np.array(Image.open(up))

    if img is not None:
        child = get_latest_child()
        if child:
            ok, msg = match_faces(child[5], img)
            st.success(msg) if ok else st.error(msg)
