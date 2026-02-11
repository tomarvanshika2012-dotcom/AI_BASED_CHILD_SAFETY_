import streamlit as st
from supabase import create_client
from twilio.rest import Client
from streamlit_geolocation import streamlit_geolocation
import os

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="AI Based Child Safety System",
    page_icon="🛡️",
    layout="centered"
)

# =====================================================
# LOAD ENV VARIABLES (FROM STREAMLIT SECRETS)
# =====================================================

SUPABASE_URL = os.getenv("https://ejwzltprnsnufyelouwk.supabase.co")
SUPABASE_KEY = os.getenv("sb_publishable_KMCudQSpc3rBICMuCd69Hw_7xoWBqK6")

TWILIO_SID = os.getenv("ACc9b9941c778de30e2ed7ba57f87cdfbc")
TWILIO_AUTH_TOKEN = os.getenv("447ac1385fd300bff05d08380e4a2bd4")
TWILIO_PHONE = os.getenv("+15075195618")
TWILIO_WHATSAPP = "whatsapp:+14155238886"  # Twilio sandbox

# Safety check
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Supabase credentials not configured.")
    st.stop()

if not TWILIO_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE:
    st.error("Twilio credentials not configured.")
    st.stop()

# Create Clients
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

# =====================================================
# APP TITLE
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
except:
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

            # Get parent details
            parent_response = supabase.table("parents")\
                .select("*")\
                .eq("child_id", child["id"])\
                .execute()

            parent = parent_response.data[0]

            # Get live location
            if location_data and location_data.get("latitude"):
                lat = location_data["latitude"]
                lon = location_data["longitude"]
                maps_link = f"https://www.google.com/maps?q={lat},{lon}"
            else:
                maps_link = "Location not available"

            # Create message
            message_body = f"""
🚨 EMERGENCY SOS ALERT 🚨

Child Name: {child['name']}
Age: {child['age']}
Clothing: {child['clothing']}

Live Location:
{maps_link}

Please respond immediately!
"""

            # Send SMS
            twilio_client.messages.create(
                body=message_body,
                from_=TWILIO_PHONE,
                to=parent["phone_no"]
            )

            # Send WhatsApp
            twilio_client.messages.create(
                body=message_body,
                from_=TWILIO_WHATSAPP,
                to=f"whatsapp:{parent['whatsapp_number']}"
            )

            st.success("🚨 SOS Sent Successfully!")

        except Exception as e:
            st.error(f"SOS Error: {e}")

else:
    st.info("No registered children found. Please register first.")

# =====================================================
# ADMIN VIEW
# =====================================================

st.divider()
st.header("📊 Registered Children")

if children:
    for child in children:
        st.markdown(f"""
        **Name:** {child['name']}  
        **Age:** {child['age']}  
        **Clothing:** {child['clothing']}  
        **Last Location:** {child['last_location']}
        """)
        st.divider()
else:
    st.write("No records available.")
