import streamlit as st
import pydeck as pdk
import pandas as pd
import numpy as np
import random
import time
import math
import sqlite3
import os
import uuid
import threading
import cv2
from PIL import Image
from datetime import datetime, timedelta
from twilio.rest import Client
from streamlit_geolocation import streamlit_geolocation

# =============================================================================
# 1. DATABASE ENGINE & CONFIG
# =============================================================================
DB_FILE = "vizag_data_fixed.db"
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Twilio Credentials (Keep these secure!)
TWILIO_SID = "ACa12e602647785572ebaf765659d26d23"
TWILIO_AUTH_TOKEN = "0e150a10a98b74ddc7d57e44fa3e01c6"
TWILIO_PHONE = "+14176076960"
TWILIO_WHATSAPP_SENDER = "whatsapp:+14155238886"
EMERGENCY_CONTACTS = ["+918130631551"] 

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Cyclone Citizens Table
    c.execute('CREATE TABLE IF NOT EXISTS citizens (phone TEXT UNIQUE, timestamp TEXT)')
    # Child SafeGuard Table
    c.execute('''CREATE TABLE IF NOT EXISTS child_registry (
                id TEXT PRIMARY KEY, name TEXT, age INTEGER, 
                clothes TEXT, loc TEXT, path TEXT, time TEXT)''')
    conn.commit()
    conn.close()

init_db()

# =============================================================================
# 2. INTEGRATED HELPER FUNCTIONS (TWILIO & FACE AI)
# =============================================================================

def send_parallel_sos(contact, msg_body, t_lang, speech, status_list):
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(body=msg_body, from_=TWILIO_PHONE, to=contact)
        client.messages.create(body=msg_body, from_=TWILIO_WHATSAPP_SENDER, to=f"whatsapp:{contact}")
        client.calls.create(twiml=f'<Response><Say language="{t_lang}">{speech}</Say></Response>',
                            from_=TWILIO_PHONE, to=contact)
        status_list.append(f"✅ Alert sent to {contact}")
    except Exception as e:
        status_list.append(f"❌ Failed {contact}: {str(e)}")

def face_match_logic(stored_path, test_np):
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    def get_face(img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        if len(faces) == 0: return None
        x,y,w,h = faces[0]
        return cv2.resize(gray[y:y+h, x:x+w], (200,200))

    stored_img = cv2.imread(stored_path)
    f1 = get_face(stored_img)
    f2 = get_face(cv2.cvtColor(test_np, cv2.COLOR_RGB2BGR))
    
    if f1 is None or f2 is None: return False, "No face detected"
    
    rec = cv2.face.LBPHFaceRecognizer_create()
    rec.train([f1], np.array([0]))
    _, conf = rec.predict(f2)
    return (True, f"Match Found ({conf:.2f})") if conf < 75 else (False, f"No Match")

# =============================================================================
# 3. GLOBAL APP CONFIG & TRANSLATIONS
# =============================================================================
# (All your existing CONFIG, VIZAG_ZONES, and TRANSLATIONS go here)
# Add a new tab key to TRANSLATIONS
for lang in TRANSLATIONS:
    TRANSLATIONS[lang]["tab5"] = "🛡️ SafeGuard" if lang == "en" else "రక్షణ"

# ... [Keep your existing generate_heatmap, generate_shelters etc. functions here] ...

# =============================================================================
# 4. MAIN APP UI
# =============================================================================

st.set_page_config(page_title="Vizag Command", page_icon="🌪️", layout="wide")

# (Keep your existing CSS and Login logic here)

if st.session_state['app_mode'] == 'dashboard':
    # Update Tabs to include Tab 5
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        get_txt('tab1'), get_txt('tab2'), get_txt('tab3'), get_txt('tab4'), get_txt('tab5')
    ])

    # ... [Keep Tab 1, 2, 3, 4 code exactly as it was] ...

    # =========================================================
    # TAB 5: CHILD SAFEGUARD (INTEGRATED FEATURE)
    # =========================================================
    with tab5:
        st.header("🛡️ AI Child SafeGuard System")
        s_col1, s_col2 = st.tabs(["📋 Registration", "🔍 AI Search & SOS"])
        
        with s_col1:
            with st.form("child_reg"):
                c_name = st.text_input("Child Name")
                c_age = st.number_input("Age", 0, 15)
                c_photo = st.file_uploader("Recent Photo", type=['jpg','png'])
                if st.form_submit_button("Register for Protection"):
                    if c_name and c_photo:
                        cid = str(uuid.uuid4())
                        path = os.path.join(UPLOAD_DIR, f"{cid}.jpg")
                        Image.open(c_photo).convert("RGB").save(path)
                        conn = sqlite3.connect(DB_FILE)
                        conn.execute("INSERT INTO child_registry VALUES (?,?,?,?,?,?,?)",
                                     (cid, c_name, c_age, "Blue", "Vizag", path, datetime.now().isoformat()))
                        conn.commit()
                        st.success(f"Registered {c_name} in Command Center Database")

        with s_col2:
            st.subheader("AI Surveillance & Emergency SOS")
            loc = streamlit_geolocation()
            
            mode = st.radio("Search Mode", ["Live Camera", "Upload CCTV Frame"])
            test_img = None
            if mode == "Live Camera":
                cam = st.camera_input("Scanner")
                if cam: test_img = np.array(Image.open(cam))
            
            if test_img is not None:
                conn = sqlite3.connect(DB_FILE)
                child = conn.execute("SELECT name, path FROM child_registry ORDER BY time DESC LIMIT 1").fetchone()
                if child:
                    matched, msg = face_match_logic(child[1], test_img)
                    if matched:
                        st.success(f"MATCH FOUND: {child[0]} identified!")
                        if st.button("🚨 TRIGGER SOS NOW"):
                            msg_body = f"🚨 SOS: {child[0]} spotted at Vizag Command Center Map."
                            statuses = []
                            for contact in EMERGENCY_CONTACTS:
                                threading.Thread(target=send_parallel_sos, 
                                               args=(contact, msg_body, "en-US", "Emergency", statuses)).start()
                            st.write("Alerts Dispatched.")
                    else: st.error(msg)