import streamlit as st
import sqlite3
import cv2
import numpy as np
from datetime import datetime
from streamlit_geolocation import streamlit_geolocation

# ================== PAGE CONFIG ==================
st.set_page_config(
    page_title="AI Child Safety System",
    page_icon="🛡️",
    layout="centered"
)
st.title("🛡️ AI Child Safety System")

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

# ================== AI MODEL ==================
FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

def extract_face(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = FACE_CASCADE.detectMultiScale(gray, 1.3, 5)
    if len(faces) == 0:
        return None
    x, y, w, h = faces[0]
    return cv2.resize(gray[y:y+h, x:x+w], (200, 200))

def compare_faces(f1, f2):
    error = np.mean((f1.astype("float") - f2.astype("float")) ** 2)
    return error < 4000

# ================== UI TABS ==================
tab1, tab2, tab3 = st.tabs(
    ["📝 Register Child", "🔍 Face Match", "🚨 Emergency SOS"]
)

# ================== TAB 1: REGISTRATION ==================
with tab1:
    st.header("Register Child")

    with st.form("register"):
        name = st.text_input("Child Name")
        age = st.number_input("Age", 1, 18)
        clothing = st.text_input("Clothing Color")
        lost_loc = st.text_input("Last Seen Location")
        photo = st.file_uploader(
            "Upload Recent Photo", ["jpg", "png", "jpeg"]
        )

        if st.form_submit_button("Register Child"):
            if name and photo:
                img_bytes = photo.read()
                img = cv2.imdecode(
                    np.frombuffer(img_bytes, np.uint8),
                    cv2.IMREAD_COLOR
                )
                face = extract_face(img)

                if face is not None:
                    conn = sqlite3.connect(DB_FILE)
                    conn.execute("""
                        INSERT INTO children
                        (name, age, photo, face, clothing_color, lost_location, registered_at)
                        VALUES (?,?,?,?,?,?,?)
                    """, (
                        name,
                        age,
                        img_bytes,
                        face.tobytes(),
                        clothing,
                        lost_loc,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ))
                    conn.commit()
                    conn.close()

                    st.success("✅ Child registered successfully")
                else:
                    st.error("❌ No face detected in photo")
            else:
                st.warning("⚠️ Name and photo are required")

# ================== TAB 2: FACE MATCH ==================
with tab2:
    st.header("Face Verification")

    conn = sqlite3.connect(DB_FILE)
    row = conn.execute("""
        SELECT name, face
        FROM children
        ORDER BY id DESC
        LIMIT 1
    """).fetchone()
    conn.close()

    if row:
        stored_name, stored_face = row
        stored_face = np.frombuffer(
            stored_face, dtype=np.uint8
        ).reshape((200, 200))

        st.info(f"Registered Child: **{stored_name}**")

        cam = st.camera_input("Scan Face")

        if cam:
            img = cv2.imdecode(
                np.frombuffer(cam.read(), np.uint8),
                cv2.IMREAD_COLOR
            )
            face = extract_face(img)

            if face is not None:
                if compare_faces(stored_face, face):
                    st.success("✅ MATCH FOUND")
                    st.balloons()
                else:
                    st.error("❌ NO MATCH")
            else:
                st.warning("⚠️ No face detected")
    else:
        st.warning("No child registered yet")

# ================== TAB 3: SOS ==================
with tab3:
    st.header("🚨 Emergency SOS")

    location = streamlit_geolocation()

    if st.button("🚨 ACTIVATE SOS"):
        if location.get("latitude"):
            lat = location["latitude"]
            lon = location["longitude"]

            conn = sqlite3.connect(DB_FILE)
            conn.execute("""
                INSERT INTO sos_logs (latitude, longitude, time)
                VALUES (?,?,?)
            """, (
                lat,
                lon,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            conn.commit()
            conn.close()

            st.error("🚨 SOS TRIGGERED!")
            st.write(f"📍 Location: {lat}, {lon}")
        else:
            st.warning("⚠️ Location permission not granted")

# ================== VIEW SOS LOGS ==================
st.subheader("📂 Recent SOS Logs")

conn = sqlite3.connect(DB_FILE)
logs = conn.execute("""
    SELECT latitude, longitude, time
    FROM sos_logs
    ORDER BY id DESC
    LIMIT 5
""").fetchall()
conn.close()

for log in logs:
    st.write(f"📍 {log[0]}, {log[1]} | ⏰ {log[2]}")
