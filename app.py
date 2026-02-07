import streamlit as st
from twilio.rest import Client
from streamlit_geolocation import streamlit_geolocation
from datetime import datetime

# --- 1. CREDENTIALS SETUP ---

TWILIO_SID = "ACa12e602647785572ebaf765659d26d23"
TWILIO_AUTH_TOKEN = "0e150a10a98b74ddc7d57e44fa3e01c6"
TWILIO_PHONE = "+14176076960"
REGISTERED_PHONE = "+918130631551"

# --- 2. UI CONFIGURATION ---
st.set_page_config(page_title="SafeGuard SOS", page_icon="🛡️", layout="centered")

st.markdown("""
    <style>
    .stButton>button {
        background-color: #ff4b4b; color: white;
        height: 250px; width: 250px; border-radius: 50%;
        font-size: 40px; font-weight: bold; border: 10px solid #bd1a1a;
        margin: auto; display: block;
        box-shadow: 0px 15px 35px rgba(255, 75, 75, 0.4);
        transition: all 0.3s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #d12e2e;
        transform: scale(1.05);
    }
    .stButton>button:active {
        transform: scale(0.95);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SIDEBAR MONITOR ---
with st.sidebar:
    st.header("🛰️ Dispatch Monitor")
    # Quick check to see if keys are populated
    if "AC" in TWILIO_SID:
        st.success("System Status: ONLINE")
    else:
        st.error("System Status: CREDENTIALS MISSING")
    
    st.divider()
    st.write(f"**Guardian Phone:** `{REGISTERED_PHONE}`")
    voice_lang = st.radio("Voice Call Language", ["English", "Hindi"])

# --- 4. CORE SOS FUNCTION ---
def trigger_emergency_protocol(lat, lon, lang):
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
        now = datetime.now().strftime("%d-%m-%Y | %I:%M %p")
        # Standard Google Maps Link
        maps_link = f"https://www.google.com/maps?q={lat},{lon}"

        # A. DISPATCH SMS
        msg_body = (
            f"🚨 CHILD SAFETY ALERT 🚨\n"
            f"SOS Button Pressed!\n"
            f"Time: {now}\n"
            f"Location: {maps_link}"
        )
        client.messages.create(body=msg_body, from_=TWILIO_PHONE, to=REGISTERED_PHONE)

        # B. DISPATCH VOICE CALL
        voice_id = "alice" if lang == "English" else "Google.hi-IN-Wavenet-A"
        speech_text = (
            "Emergency alert! Your child has triggered the SOS system. Check your messages for their location."
            if lang == "English" else 
            "आपातकालीन अलर्ट। आपके बच्चे ने सुरक्षा बटन दबाया है। कृपया स्थान की जानकारी के लिए अपने संदेश देखें।"
        )

        client.calls.create(
            twiml=f'<Response><Say voice="{voice_id}">{speech_text}</Say></Response>',
            from_=TWILIO_PHONE,
            to=REGISTERED_PHONE
        )
        return True, "Alert Dispatched Successfully."
    except Exception as e:
        return False, str(e)

# --- 5. MAIN INTERFACE ---
st.title("🛡️ SafeGuard SOS")
st.write("Instant Emergency Response Hub")

# Geolocation component
location = streamlit_geolocation()

if st.button("🆘 SOS"):
    if location['latitude'] and location['longitude']:
        with st.status("Executing Emergency Protocols...", expanded=True) as status:
            lat, lon = location['latitude'], location['longitude']
            success, info = trigger_emergency_protocol(lat, lon, voice_lang)
            
            if success:
                status.update(label="✅ ALERTS SENT", state="complete")
                st.success(f"SMS and Voice call sent to {REGISTERED_PHONE}")
                st.balloons()
            else:
                status.update(label="❌ SYSTEM FAILURE", state="error")
                st.error(f"Error: {info}")
    else:
        st.error("Critical Error: Location access denied. Please enable GPS in your browser.")

if location['latitude']:
    st.divider()
    st.write(f"**Current Coordinates:** {location['latitude']}, {location['longitude']}")
    st.write(f"**Live Preview:** [View on Google Maps](https://www.google.com/maps?q={location['latitude']},{location['longitude']})")