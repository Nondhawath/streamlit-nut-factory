import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date
import altair as alt
from io import BytesIO

# เชื่อมต่อ Google Sheets
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(credentials)
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1gIBZmGn86zzJWECO7Kzy5c0ibOdN1N_3Ys58M80b0kk")

# โหลดข้อมูล
machines_df = pd.DataFrame(sheet.worksheet("Machines").get_all_records())
employees_df = pd.DataFrame(sheet.worksheet("Employees").get_all_records())
breakdowns_df = pd.DataFrame(sheet.worksheet("Breakdowns").get_all_records())
oee_log_df = pd.DataFrame(sheet.worksheet("OEE_Log").get_all_records())

# ฟังก์ชันคำนวณ OEE
def calculate_oee(df):
    df["Availability"] = df["Runtime"] / (df["Runtime"] + df["Downtime"])
    df["Performance"] = df["Runtime"] / (df["TotalProduced"].replace(0, 1))
    df["Quality"] = (df["TotalProduced"] - df["Defects"]) / df["TotalProduced"].replace(0, 1)
    df["OEE"] = df["Availability"] * df["Performance"] * df["Quality"]
    return df

# UI
st.title("SCS OEE Performance")

tab1, tab2, tab3 = st.tabs(["📝 บันทึก OEE", "📈 Dashboard", "📤 Export"])

# Tab 1: ฟอร์มกรอกข้อมูล
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

# Tab 2: Dashboard วิเคราะห์
with tab2:
    if not oee_log_df.empty:
        df = oee_log_df.copy()
        numeric_cols = ["Runtime", "Downtime", "Defects", "TotalProduced"]
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
        df = calculate_oee(df)

        # เติมข้อมูลแผนก
        df = df.merge(machines_df[["MachineID", "Department"]], on="MachineID", how="left")

        department = st.selectbox("เลือกแผนก", options=["ทั้งหมด"] + sorted(df["Department"].dropna().unique().tolist()))
        if department != "ทั้งหมด":
            df = df[df["Department"] == department]

        st.dataframe(df[["Date", "Department", "MachineID", "Availability", "Performance", "Quality", "OEE"]])

        avg_oee = df["OEE"].mean() * 100
        st.metric("📊 ค่าเฉลี่ย OEE", f"{avg_oee:.2f}%")

        # กราฟ
        df["Date"] = pd.to_datetime(df["Date"])
        chart = alt.Chart(df).mark_line(point=True).encode(
            x="Date:T",
            y=alt.Y("OEE:Q", title="OEE"),
            color="MachineID:N",
            tooltip=["Date", "MachineID", "OEE"]
        ).properties(width=700, height=400, title="📈 OEE รายวัน")

        st.altair_chart(chart, use_container_width=True)
    else:
        st.warning("ยังไม่มีข้อมูลใน OEE_Log")

# Tab 3: Export Excel
with tab3:
    if not oee_log_df.empty:
        df = oee_log_df.copy()
        numeric_cols = ["Runtime", "Downtime", "Defects", "TotalProduced"]
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
        df = calculate_oee(df)

        # สร้าง Excel
        towrite = BytesIO()
        with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='OEE_Report')

        st.download_button(
            label="📥 ดาวน์โหลดรายงาน OEE (Excel)",
            data=towrite.getvalue(),
            file_name="OEE_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("ไม่มีข้อมูลให้ดาวน์โหลด")
