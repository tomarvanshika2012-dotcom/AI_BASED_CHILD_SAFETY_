import streamlit as st
from supabase import create_client
from twilio.rest import Client
from streamlit_geolocation import streamlit_geolocation

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="AI Based Child Safety System",
    page_icon="🛡️",
    layout="centered"
)

# =====================================================
# LOAD SECRETS (STREAMLIT CLOUD)
# =====================================================

try:
    SUPABASE_URL = st.secrets["https://ejwzltprnsnufyelouwk.supabase.co"]
    SUPABASE_KEY = st.secrets["sb_publishable_KMCudQSpc3rBICMuCd69Hw_7xoWBqK6"]

    TWILIO_SID = st.secrets["ACc9b9941c778de30e2ed7ba57f87cdfbc"]
    TWILIO_AUTH_TOKEN = st.secrets["447ac1385fd300bff05d08380e4a2bd4"]
    TWILIO_PHONE = st.secrets["+15075195618"]

except Exception:
    st.error("❌ Secrets not configured. Please add them in Streamlit Cloud settings.")
    st.stop()

TWILIO_WHATSAPP = "whatsapp:+14155238886"

# Create Clients
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

# =====================================================
# TITLE
# =====================================================

st.title("🛡️ AI Based Child Safety System")
st.markdown("Cloud-connected child registration and emergency SOS system.")

# =====================================================
# CHILD REGISTRATION
# =====================================================

st.header("👶 Register Child")

with st.form("child_registration_form"):

    name = st.text_input("Child Name")
    age = st.number_input("Age", min_value=1, max_value=18)
    clothing = st.text_input("Clothing Description")
    last_location = st.text_input("Last Known Location")

    st.subheader("👨‍👩‍👧 Parent Details")

    parent_name = st.text_input("Parent Name")
    phone_no = st.text_input("Parent Phone Number (+91...)")
    whatsapp_number = st.text_input("Parent WhatsApp Number (+91...)")

    submitted = st.form_submit_button("Register")

    if submitted:
        if not name or not parent_name:
            st.warning("Please fill required fields.")
        else:
            try:
                # Insert child
                child_data = {
                    "name": name,
                    "age": age,
                    "clothing": clothing,
                    "last_location": last_location
                }

                child_response = supabase.table("children").insert(child_data).execute()
                child_id = child_response.data[0]["id"]

                # Insert parent
                parent_data = {
                    "child_id": child_id,
                    "parent_name": parent_name,
                    "phone_no": phone_no,
                    "whatsapp_number": whatsapp_number
                }
r
                supabase.table("parents").insert(parent_data).execute()

                st.success("✅ Child Registered Successfully!")

            except Exception as e:
                st.error(f"Database Error: {e}")

# =====================================================
# SOS SECTION
# =====================================================

st.divider()
st.header("🚨 Emergency SOS")

try:
    children_response = supabase.table("children").select("*").execute()
    children = children_response.data
except Exception:
    children = []

if children:

    child_names = [child["name"] for child in children]
    selected_child = st.selectbox("Select Child", child_names)

    st.info("Allow location access when prompted.")

    location_data = streamlit_geolocation()

    if st.button("🚨 SEND SOS ALERT"):

        try:
            # Get selected child
            child = next(c for c in children if c["name"] == selected_child)
