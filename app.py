import streamlit as st
from supabase import create_client
from twilio.rest import Client
from streamlit_geolocation import streamlit_geolocation
from datetime import datetime

# ============================================
# CONFIGURATION
# ============================================

st.set_page_config(page_title="Child Safety SOS", page_icon="🛡️")

# 🔹 SUPABASE CONFIG
SUPABASE_URL = "https://ejwzltprnsnufyelouwk.supabase.co"
SUPABASE_KEY = "sb_publishable_KMCudQSpc3rBICMuCd69Hw_7xoWBqK6"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🔹 TWILIO CONFIG
TWILIO_SID = "ACc9b9941c778de30e2ed7ba57f87cdfbc"
TWILIO_AUTH_TOKEN = "447ac1385fd300bff05d08380e4a2bd4"
TWILIO_PHONE = "+15075195618"  # Twilio SMS number
TWILIO_WHATSAPP = "whatsapp:+14155238886"  # Twilio WhatsApp sandbox number

twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

# ============================================
# TITLE
# ============================================

st.title("🛡️ Child Safety System")

# ============================================
# REGISTER CHILD SECTION
# ============================================

with st.form("child_form"):

    st.subheader("👶 Child Information")

    name = st.text_input("Child Name")
    age = st.number_input("Age", min_value=1, max_value=18)
    clothing = st.text_input("Clothing Description")
    location = st.text_input("Last Known Location")

    st.subheader("👨‍👩‍👧 Parent Information")

    parent_name = st.text_input("Parent Name")
    phone_no = st.text_input("Phone Number (+91...)")
    whatsapp_number = st.text_input("WhatsApp Number (+91...)")

    submitted = st.form_submit_button("Register Child")

    if submitted:
        try:
            child_data = {
                "name": name,
                "age": age,
                "clothing": clothing,
                "last_location": location
            }

            child_response = supabase.table("children").insert(child_data).execute()
            child_id = child_response.data[0]["id"]

            parent_data = {
                "child_id": child_id,
                "parent_name": parent_name,
                "phone_no": phone_no,
                "whatsapp_number": whatsapp_number
            }

            supabase.table("parents").insert(parent_data).execute()

            st.success("✅ Child Registered Successfully!")

        except Exception as e:
            st.error(f"Error: {e}")

# ============================================
# SOS SECTION
# ============================================

st.divider()
st.subheader("🚨 EMERGENCY SOS")

children = supabase.table("children").select("*").execute().data

if children:
    child_names = [child["name"] for child in children]
    selected_child = st.selectbox("Select Child", child_names)

    location_data = streamlit_geolocation()

    if st.button("🚨 SEND SOS ALERT"):

        try:
            # Get selected child details
            child = next(c for c in children if c["name"] == selected_child)

            # Get parent info
            parent = supabase.table("parents").select("*").eq("child_id", child["id"]).execute().data[0]

            # Get live location
            if location_data and location_data["latitude"]:
                lat = location_data["latitude"]
                lon = location_data["longitude"]
                maps_link = f"https://www.google.com/maps?q={lat},{lon}"
            else:
                maps_link = "Location not available"

            # Create SOS message
            message_body = f"""
🚨 EMERGENCY SOS ALERT 🚨

Child Name: {child['name']}
Age: {child['age']}
Clothing: {child['clothing']}

Live Location:
{maps_link}

Please respond immediately!
"""

            # 🔹 Send SMS
            twilio_client.messages.create(
                body=message_body,
                from_=TWILIO_PHONE,
                to=parent["phone_no"]
            )

            # 🔹 Send WhatsApp
            twilio_client.messages.create(
                body=message_body,
                from_=TWILIO_WHATSAPP,
                to=f"whatsapp:{parent['whatsapp_number']}"
            )

            st.success("🚨 SOS Sent Successfully!")

        except Exception as e:
            st.error(f"SOS Error: {e}")
else:
    st.info("No registered children found.")
