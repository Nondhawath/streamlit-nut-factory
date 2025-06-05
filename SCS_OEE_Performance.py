import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date

# เชื่อมต่อ Google Sheets
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(credentials)

sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1gIBZmGn86zzJWECO7Kzy5c0ibOdN1N_3Ys58M80b0kk")

# โหลดชีตต่างๆ
machines_df = pd.DataFrame(sheet.worksheet("Machines").get_all_records())
employees_df = pd.DataFrame(sheet.worksheet("Employees").get_all_records())
breakdowns_df = pd.DataFrame(sheet.worksheet("Breakdowns").get_all_records())
oee_log_df = pd.DataFrame(sheet.worksheet("OEE_Log").get_all_records())

# ส่วน UI
st.title("SCS OEE Performance")

tab1, tab2 = st.tabs(["📝 บันทึก OEE", "📊 ข้อมูลทั้งหมด"])

# 📝 Tab 1: ฟอร์มบันทึกข้อมูล
with tab1:
    with st.form("log_oee_form"):
        col1, col2 = st.columns(2)
        with col1:
            log_date = st.date_input("วันที่", value=date.today())
            shift = st.selectbox("กะการทำงาน", [1, 2, 3])
            machine_id = st.selectbox("เครื่องจักร", machines_df["MachineID"])
        with col2:
            employee_id = st.selectbox("พนักงาน", employees_df["EmployeeID"])
            runtime = st.number_input("Runtime (นาที)", min_value=0)
            downtime = st.number_input("Downtime (นาที)", min_value=0)
            defects = st.number_input("Defects (จำนวน)", min_value=0)
            total_produced = st.number_input("Total Produced (จำนวน)", min_value=0)

        submitted = st.form_submit_button("✅ บันทึกข้อมูล")

        if submitted:
            oee_sheet = sheet.worksheet("OEE_Log")
            new_row = [str(log_date), shift, machine_id, employee_id, runtime, downtime, defects, total_produced]
            oee_sheet.append_row(new_row)
            st.success("✅ บันทึกข้อมูลสำเร็จแล้ว!")

# 📊 Tab 2: แสดงข้อมูลทั้งหมด
with tab2:
    st.subheader("เครื่องจักร")
    st.dataframe(machines_df)

    st.subheader("พนักงาน")
    st.dataframe(employees_df)

    st.subheader("Breakdowns")
    st.dataframe(breakdowns_df)

    st.subheader("OEE Log")
    st.dataframe(oee_log_df)
