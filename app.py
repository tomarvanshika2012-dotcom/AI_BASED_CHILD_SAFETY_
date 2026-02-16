import streamlit as st
import requests
import json
import cv2
import numpy as np
import face_recognition
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
from twilio.rest import Client
from streamlit_geolocation import streamlit_geolocation

# ================= CONFIG =================
BACKEND_URL = "http://127.0.0.1:5000"

TWILIO_SID = "ACc9b9941c778de30e2ed7ba57f87cdfbc"
TWILIO_AUTH = "999fa232d9d9e8523039eab01ad41288"
TWILIO_PHONE = "+15075195618"

twilio_client = Client(TWILIO_SID, TWILIO_AUTH)

st.set_page_config(page_title="AI Child Safety", page_icon="🛡️")
st.title("🛡️ AI Child Safety System")

# ================= LOAD CHILDREN =================
def load_children():
    try:
        return requests.get(f"{BACKEND_URL}/children").json()
    except:
        st.error("❌ Backend not running")
        return []

children = load_children()

# ================= TABS =================
tab1, tab2, tab3, tab4 = st.tabs([
    "👶 Register Child",
    "🚨 Emergency SOS",
    "🎥 Live Face Recognition",
    "📋 View Children"
])

# ==================================================
# TAB 1 — REGISTER
# ==================================================
with tab1:

    st.header("Register Child")

    name = st.text_input("Child Name")
    age = st.number_input("Age", 1, 18)
    clothing = st.text_input("Clothing")
    last_location = st.text_input("Last Location")
    parent_name = st.text_input("Parent Name")
    phone_no = st.text_input("Parent Phone (+91...)")
    whatsapp_no = st.text_input("Parent WhatsApp")

    uploaded = st.file_uploader("Upload Clear Face Photo")

    face_encoding_json = None

    if uploaded:
        image = face_recognition.load_image_file(uploaded)
        encodings = face_recognition.face_encodings(image)

        if encodings:
            face_encoding_json = json.dumps(encodings[0].tolist())
            st.success("✅ Face Detected")
        else:
            st.error("❌ No face detected")

    if st.button("Register Child"):

        if not face_encoding_json:
            st.warning("Upload valid face image")
        else:
            data = {
                "name": name,
                "age": age,
                "clothing": clothing,
                "last_location": last_location,
                "parent_name": parent_name,
                "phone_no": phone_no,
                "whatsapp_no": whatsapp_no,
                "face_encoding": face_encoding_json
            }

            res = requests.post(f"{BACKEND_URL}/register", json=data)

            if res.status_code == 200:
                st.success("✅ Registered Successfully")
            else:
                st.error("❌ Registration Failed")

# ==================================================
# TAB 2 — SOS
# ==================================================
with tab2:

    st.header("Emergency SOS")

    if children:

        names = [c["name"] for c in children]
        selected = st.selectbox("Select Child", names)

        location = streamlit_geolocation()

        if st.button("SEND SOS"):

            if not location or not location.get("latitude"):
                st.error("❌ Location not available")
            else:
                child = next(c for c in children if c["name"] == selected)

                lat = location["latitude"]
                lon = location["longitude"]

                message = f"""
🚨 CHILD SOS ALERT 🚨
Child: {child['name']}
Location: https://www.google.com/maps?q={lat},{lon}
"""

                try:
                    # SMS
                    twilio_client.messages.create(
                        body=message,
                        from_=TWILIO_PHONE,
                        to=child["phone_no"]
                    )

                    # CALL
                    twilio_client.calls.create(
                        twiml="""
                        <Response>
                            <Say>
                                Emergency alert.
                                A child safety SOS has been triggered.
                                Please check the message immediately.
                            </Say>
                        </Response>
                        """,
                        from_=TWILIO_PHONE,
                        to=child["phone_no"]
                    )

                    st.success("✅ SMS + Call Sent")

                except Exception as e:
                    st.error(f"Twilio Error: {e}")

    else:
        st.info("No children registered")

# ==================================================
# TAB 3 — LIVE FACE RECOGNITION
# ==================================================
with tab3:

    st.header("Live Face Recognition")

    if children:

        names = [c["name"] for c in children]
        selected_face = st.selectbox("Select Child", names, key="face_tab")

        child = next(c for c in children if c["name"] == selected_face)

        if child["face_encoding"]:

            known_encoding = np.array(json.loads(child["face_encoding"]))

            class VideoProcessor(VideoTransformerBase):
                def recv(self, frame):
                    img = frame.to_ndarray(format="bgr24")
                    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                    face_locations = face_recognition.face_locations(rgb)
                    face_encodings = face_recognition.face_encodings(rgb, face_locations)

                    for encoding, location in zip(face_encodings, face_locations):

                        matches = face_recognition.compare_faces(
                            [known_encoding], encoding
                        )

                        top, right, bottom, left = location

                        if True in matches:
                            color = (0, 255, 0)
                            label = "MATCH"
                        else:
                            color = (0, 0, 255)
                            label = "NO MATCH"

                        cv2.rectangle(img, (left, top), (right, bottom), color, 2)
                        cv2.putText(
                            img,
                            label,
                            (left, top - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.9,
                            color,
                            2,
                        )

                    return img

            webrtc_streamer(
                key="face-recognition",
                video_processor_factory=VideoProcessor,
                media_stream_constraints={"video": True, "audio": False},
            )

        else:
            st.warning("No face encoding stored")

    else:
        st.info("No children registered")

# ==================================================
# TAB 4 — VIEW CHILDREN
# ==================================================
with tab4:

    st.header("Registered Children")

    if children:
        for c in children:
            st.write(f"👶 {c['name']} | 📞 {c['phone_no']}")
    else:
        st.info("No data found")
