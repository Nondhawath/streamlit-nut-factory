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

# โหลดข้อมูลจากชีตต่าง ๆ
machines_df = pd.DataFrame(sheet.worksheet("Machines").get_all_records())
employees_df = pd.DataFrame(sheet.worksheet("Employees").get_all_records())
breakdowns_df = pd.DataFrame(sheet.worksheet("Breakdowns").get_all_records())
oee_log_df = pd.DataFrame(sheet.worksheet("OEE_Log").get_all_records())

# ฟังก์ชันคำนวณ OEE
def calculate_oee(df):
    df["Availability"] = df["Runtime"] / (df["Runtime"] + df["Downtime"])
    df["Performance"] = df["Runtime"] / (df["TotalProduced"].replace(0, 1) * 1)  # สมมุติ Cycle time = 1 นาที
    df["Quality"] = (df["TotalProduced"] - df["Defects"]) / df["TotalProduced"].replace(0, 1)
    df["OEE"] = df["Availability"] * df["Performance"] * df["Quality"]
    return df

# UI Layout
st.title("SCS OEE Performance")

tab1, tab2, tab3 = st.tabs(["📝 บันทึก OEE", "📊 ดูข้อมูลทั้งหมด", "📈 Dashboard OEE"])

# TAB 1: ฟอร์มบันทึก OEE
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

# TAB 2: ดูข้อมูลทั้งหมด
with tab2:
    st.subheader("เครื่องจักร")
    st.dataframe(machines_df)

    st.subheader("พนักงาน")
    st.dataframe(employees_df)

    st.subheader("Breakdowns")
    st.dataframe(breakdowns_df)

    st.subheader("OEE Log")
    st.dataframe(oee_log_df)

# TAB 3: Dashboard วิเคราะห์ OEE
with tab3:
    if not oee_log_df.empty:
        df = oee_log_df.copy()
        numeric_cols = ["Runtime", "Downtime", "Defects", "TotalProduced"]
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

        df = calculate_oee(df)
        st.subheader("ตารางวิเคราะห์ OEE")
        st.dataframe(df[["Date", "MachineID", "Availability", "Performance", "Quality", "OEE"]])

        avg_oee = df["OEE"].mean() * 100
        st.metric("📊 ค่าเฉลี่ย OEE", f"{avg_oee:.2f}%")
    else:
        st.warning("ยังไม่มีข้อมูลใน OEE_Log")
