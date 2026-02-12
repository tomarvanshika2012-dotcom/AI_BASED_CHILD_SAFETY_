import streamlit as st
from supabase import create_client
from twilio.rest import Client
from streamlit_geolocation import streamlit_geolocation

# ===============================
# PAGE CONFIG
# ===============================

st.set_page_config(
    page_title="AI Child Safety System",
    page_icon="🛡️",
    layout="centered"
)

st.title("🛡️ AI Child Safety System")

# ===============================
# LOAD SECRETS
# ===============================

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

    TWILIO_SID = st.secrets["TWILIO_SID"]
    TWILIO_AUTH_TOKEN = st.secrets["TWILIO_AUTH_TOKEN"]
    TWILIO_PHONE = st.secrets["TWILIO_PHONE"]
    TWILIO_WHATSAPP = st.secrets["TWILIO_WHATSAPP"]

except Exception:
    st.error("❌ Secrets not configured properly in Streamlit Cloud.")
    st.stop()

# ===============================
# CREATE CLIENTS
# ===============================

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"❌ Supabase Connection Failed: {e}")
    st.stop()

try:
    twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
except:
    twilio_client = None

# ===============================
# CHILD REGISTRATION
# ===============================

st.header("👶 Register Child")

with st.form("child_form"):
    name = st.text_input("Child Name")
    age = st.number_input("Age", 1, 18)
    clothing = st.text_input("Clothing Description")
    last_location = st.text_input("Last Known Location")

    parent_name = st.text_input("Parent Name")
    phone_no = st.text_input("Parent Phone (+91...)")
    whatsapp_no = st.text_input("Parent WhatsApp (+91...)")

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

                result = supabase.table("children").insert(child_data).execute()
                child_id = result.data[0]["id"]

                # Insert parent
                parent_data = {
                    "child_id": child_id,
                    "parent_name": parent_name,
                    "phone_no": phone_no,
                    "whatsapp_number": whatsapp_no
                }

                supabase.table("parents").insert(parent_data).execute()

                st.success("✅ Child Registered Successfully!")

            except Exception as e:
                st.error(f"Database Error: {e}")

# ===============================
# SOS SECTION
# ===============================

st.divider()
st.header("🚨 Emergency SOS")

try:
    children_data = supabase.table("children").select("*").execute()
    children = children_data.data
except:
    children = []

if children:
    child_names = [child["name"] for child in children]
    selected_child = st.selectbox("Select Child", child_names)

    location = streamlit_geolocation()

    if st.button("🚨 SEND SOS ALERT"):

        if not location.get("latitude"):
            st.warning("Please allow location access.")
            st.stop()

        try:
            child = next(c for c in children if c["name"] == selected_child)

            parent_data = supabase.table("parents") \
                .select("*") \
                .eq("child_id", child["id"]) \
                .execute()

            parents = parent_data.data

            if not parents:
                st.warning("No parent found for this child.")
                st.stop()

            parent = parents[0]

            message = f"""
🚨 CHILD SOS ALERT 🚨
Child: {child['name']}
Location: https://www.google.com/maps?q={location['latitude']},{location['longitude']}
"""

            # Send SMS
            twilio_client.messages.create(
                body=message,
                from_=TWILIO_PHONE,
                to=parent["phone_no"]
            )

            # Send WhatsApp
            twilio_client.messages.create(
                body=message,
                from_=TWILIO_WHATSAPP,
                to=f"whatsapp:{parent['whatsapp_number']}"
            )

            # Make Call
            twilio_client.calls.create(
                twiml=f"<Response><Say>Emergency alert for {child['name']}</Say></Response>",
                from_=TWILIO_PHONE,
                to=parent["phone_no"]
            )

            st.success("✅ SOS Alert Sent Successfully!")

        except Exception as e:
            st.error(f"SOS Error: {e}")

else:
    st.info("No children registered yet.")
