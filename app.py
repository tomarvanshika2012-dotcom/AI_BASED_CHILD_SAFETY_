import streamlit as st
import requests
import cv2
import face_recognition
import av
import numpy as np
import speech_recognition as sr
import queue
import threading
from twilio.rest import Client
from streamlit_geolocation import streamlit_geolocation
from streamlit_webrtc import (
    webrtc_streamer,
    WebRtcMode,
    AudioProcessorBase,
    VideoProcessorBase,
)

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(page_title="AI Child Safety System", page_icon="🛡️")
st.title("🛡️ AI Child Safety System")

BACKEND_URL = "http://127.0.0.1:5000"

TWILIO_SID = "ACc9b9941c778de30e2ed7ba57f87cdfbc"
TWILIO_AUTH = "999fa232d9d9e8523039eab01ad41288"
TWILIO_PHONE = "+15075195618"

twilio_client = Client(TWILIO_SID, TWILIO_AUTH)

# =====================================================
# DISTRESS WORDS
# =====================================================

VOICE_KEYWORDS = [
    "help", "save me", "danger",
    "bachao", "madad", "bacha lo",
    "please help", "mummy help",
    "papa help"
]

audio_queue = queue.Queue()

# =====================================================
# SOS FUNCTION
# =====================================================

def send_sos(phone, message):
    try:
        twilio_client.messages.create(
            body=message,
            from_=TWILIO_PHONE,
            to=phone
        )

        twilio_client.calls.create(
            twiml="<Response><Say>Emergency alert triggered</Say></Response>",
            from_=TWILIO_PHONE,
            to=phone
        )

        st.success("✅ SOS Sent Successfully")

    except Exception as e:
        st.error(f"Twilio Error: {e}")

# =====================================================
# AUDIO PROCESSOR
# =====================================================

class AudioProcessor(AudioProcessorBase):
    def recv(self, frame):
        audio = frame.to_ndarray()
        audio_queue.put(audio)
        return frame

def background_voice_listener(child, location):
    recognizer = sr.Recognizer()

    while True:
        try:
            if not audio_queue.empty():
                audio_data = audio_queue.get()
                audio_bytes = audio_data.tobytes()

                audio_obj = sr.AudioData(audio_bytes, 16000, 2)
                text = recognizer.recognize_google(audio_obj).lower()

                for word in VOICE_KEYWORDS:
                    if word in text:
                        st.warning(f"🚨 Voice Trigger Detected: {word}")

                        message = f"""
🚨 AUTO VOICE SOS ALERT 🚨
Child: {child['name']}
Location: https://www.google.com/maps?q={location['latitude']},{location['longitude']}
"""

                        send_sos(child["phone_no"], message)
                        return

        except:
            pass

# =====================================================
# FACE PROCESSOR
# =====================================================

class FaceProcessor(VideoProcessorBase):
    def __init__(self):
        self.known_encoding = None

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        rgb = img[:, :, ::-1]

        faces = face_recognition.face_locations(rgb)
        encodings = face_recognition.face_encodings(rgb, faces)

        for (top, right, bottom, left), encoding in zip(faces, encodings):
            cv2.rectangle(img, (left, top), (right, bottom), (0, 255, 0), 2)

        return av.VideoFrame.from_ndarray(img, format="bgr24")

# =====================================================
# TABS
# =====================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "👶 Register",
    "🚨 Manual SOS",
    "🎥 Live Face Recognition",
    "🎤 Voice Auto SOS"
])

# =====================================================
# TAB 1 — REGISTER
# =====================================================

with tab1:
    st.header("Child Registration")

    name = st.text_input("Child Name")
    age = st.number_input("Age", 1, 18)
    clothing = st.text_input("Clothing")
    location_text = st.text_input("Last Known Location")
    parent_name = st.text_input("Parent Name")
    phone_no = st.text_input("Parent Phone (+91...)")

    if st.button("Register Child"):
        data = {
            "name": name,
            "age": age,
            "clothing": clothing,
            "last_location": location_text,
            "parent_name": parent_name,
            "phone_no": phone_no
        }

        try:
            response = requests.post(f"{BACKEND_URL}/register", json=data)

            if response.status_code == 200:
                st.success("✅ Registration Successful")
            else:
                st.error("Registration Failed")
        except:
            st.error("Backend not running")

# =====================================================
# TAB 2 — MANUAL SOS
# =====================================================

with tab2:
    st.header("Emergency SOS")

    try:
        children = requests.get(f"{BACKEND_URL}/children").json()
    except:
        children = []
        st.error("Backend not running")

    if children:
        names = [c["name"] for c in children]
        selected = st.selectbox("Select Child", names, key="manual_sos_select")

        location = streamlit_geolocation()

        if st.button("SEND SOS"):
            child = next(c for c in children if c["name"] == selected)

            message = f"""
🚨 CHILD SOS ALERT 🚨
Child: {child['name']}
Location: https://www.google.com/maps?q={location['latitude']},{location['longitude']}
"""

            send_sos(child["phone_no"], message)

# =====================================================
# TAB 3 — LIVE FACE RECOGNITION
# =====================================================

with tab3:
    st.header("Live Face Recognition")

    webrtc_streamer(
        key="face-recognition",
        mode=WebRtcMode.SENDRECV,
        video_processor_factory=FaceProcessor,
        media_stream_constraints={"video": True, "audio": False},
    )

# =====================================================
# TAB 4 — VOICE AUTO SOS
# =====================================================

with tab4:
    st.header("Background Voice Monitoring")

    try:
        children = requests.get(f"{BACKEND_URL}/children").json()
    except:
        children = []
        st.error("Backend not running")

    if children:
        names = [c["name"] for c in children]
        selected_name = st.selectbox("Select Child", names, key="voice_sos_select")

        selected_child = next(c for c in children if c["name"] == selected_name)

        location = streamlit_geolocation()

        st.info("Allow microphone access. System will listen continuously.")

        webrtc_streamer(
            key="voice-detect",
            audio_processor_factory=AudioProcessor,
            media_stream_constraints={"audio": True, "video": False},
        )

        if st.button("Start Voice Monitoring"):
            thread = threading.Thread(
                target=background_voice_listener,
                args=(selected_child, location),
                daemon=True,
            )
            thread.start()

            st.success("🎤 Voice Monitoring Started")
