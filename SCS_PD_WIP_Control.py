import streamlit as st
import json
import firebase_admin
from firebase_admin import credentials

# ดึงข้อมูลจาก Streamlit Secrets
firebase_credentials = st.secrets["firebase_credentials"]

# ตรวจสอบว่าข้อมูลใน Streamlit Secrets เป็น JSON string และแปลงเป็น dictionary
if isinstance(firebase_credentials, str):  # ตรวจสอบว่าเป็น JSON string
    firebase_credentials_dict = json.loads(firebase_credentials)  # แปลงจาก JSON string เป็น dictionary
else:
    st.error("Firebase credentials must be a JSON string.")
    firebase_credentials_dict = {}

# เชื่อมต่อกับ Firebase Admin SDK
cred = credentials.Certificate(firebase_credentials_dict)
firebase_admin.initialize_app(cred)

# หากเชื่อมต่อสำเร็จ
st.success("Firebase Admin SDK Initialized successfully!")
