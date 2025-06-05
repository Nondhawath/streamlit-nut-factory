import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# เชื่อมต่อ Google Sheets
scope = ["https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive"]

credentials = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(credentials)
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1gIBZmGn86zzJWECO7Kzy5c0ibOdN1N_3Ys58M80b0kk")

# อ่านข้อมูลจากชีตต่างๆ
machines_df = pd.DataFrame(sheet.worksheet("Machines").get_all_records())
employees_df = pd.DataFrame(sheet.worksheet("Employees").get_all_records())
breakdowns_df = pd.DataFrame(sheet.worksheet("Breakdowns").get_all_records())
oee_log_df = pd.DataFrame(sheet.worksheet("OEE_Log").get_all_records())

# แสดงผลบนหน้าเว็บ
st.title("SCS OEE Performance - ทดสอบการเชื่อมต่อ")
st.subheader("เครื่องจักร")
st.dataframe(machines_df)

st.subheader("พนักงาน")
st.dataframe(employees_df)

st.subheader("Breakdowns")
st.dataframe(breakdowns_df)

st.subheader("OEE Log")
st.dataframe(oee_log_df)
