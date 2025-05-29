import streamlit as st 
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import os
from io import BytesIO

st.set_page_config(page_title="Sorting Process App", layout="wide")

DATA_FILE = "sorting_report_updated.xlsx"

# ----- Upload Excel Files -----
st.sidebar.header("📂 อัปโหลดไฟล์อ้างอิง")
emp_file = st.sidebar.file_uploader("อัปโหลดรายชื่อพนักงาน (Excel)", type=["xlsx"])
part_file = st.sidebar.file_uploader("อัปโหลดรายการรหัสงาน (Excel)", type=["xlsx"])

# ----- Load Employee & Part Code Data -----
def load_data(emp_file, part_file):
    df_emp = pd.read_excel(emp_file)
    df_part = pd.read_excel(part_file)
    return df_emp, df_part

if emp_file and part_file:
    df_emp, df_part = load_data(emp_file, part_file)

    employees = df_emp['ชื่อ'].dropna().unique().tolist()
    leaders = df_emp[df_emp['ตำแหน่ง'].str.contains("Leader", na=False)]['ชื่อ'].unique().tolist()
    part_codes = df_part['รหัส'].dropna().unique().tolist()

    # ----- Load Existing Report or Create New -----
    def load_report():
        if os.path.exists(DATA_FILE):
            return pd.read_excel(DATA_FILE)
        else:
            columns = [
                "Timestamp", "Employee", "Part Code", "Total Checked", "NG", "Un-Tested", "Status", 
                "Current Process", "Rework Time", "Leader", "Oil Cleaning Time", "Sender"
            ]
            return pd.DataFrame(columns=columns)

    report_df = load_report()

    # ----- Form Input -----
    st.header("📋 กรอกข้อมูลผลการตรวจสอบจากแผนก Sorting")
    st.markdown("---")

    with st.form("sorting_form"):
        col1, col2 = st.columns(2)
        with col1:
            employee = st.selectbox("ชื่อพนักงาน", employees)
            part_code = st.text_input("รหัสงาน (สามารถพิมพ์หรือเลือก)", "")
            part_code_dropdown = st.selectbox("เลือกรหัสงานจากรายการ", ["ไม่เลือก"] + part_codes)
            if part_code_dropdown != "ไม่เลือก":
                part_code = part_code_dropdown

            total_checked = st.number_input("จำนวนที่ตรวจ", min_value=0)
            ng = st.number_input("จำนวน NG", min_value=0)
            untested = st.number_input("จำนวนที่ตรวจไม่ทัน (Un-Tested)", min_value=0)

        with col2:
            status = st.selectbox("สถานะ", ["งาน NG จากเครื่อง", "Rework", "Scrap"])
            current_process = "Sorting"
            rework_time = ""
            leader = ""
            oil_time = ""
            sender = ""

            if status == "Rework":
                leader = st.selectbox("เลือก Leader ผู้ตัดสินใจ", leaders, key="leader_select")
                if st.form_submit_button("📤 ส่งงานไปแผนก Oil Cleaning"):
                    rework_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            elif current_process == "Oil Cleaning":
                sender = st.selectbox("ชื่อผู้ส่งกลับ", employees, key="sender_select")
                if st.form_submit_button("📤 ส่งงานกลับไป Sorting"):
                    oil_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        submitted = st.form_submit_button("✅ บันทึกข้อมูล")
        if submitted:
            new_data = pd.DataFrame([{
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Employee": employee,
                "Part Code": part_code,
                "Total Checked": total_checked,
                "NG": ng,
                "Un-Tested": untested,
                "Status": status,
                "Current Process": current_process,
                "Rework Time": rework_time,
                "Leader": leader,
                "Oil Cleaning Time": oil_time,
                "Sender": sender
            }])
            report_df = pd.concat([report_df, new_data], ignore_index=True)
            report_df.to_excel(DATA_FILE, index=False)
            st.success("✅ บันทึกข้อมูลเรียบร้อยแล้ว")

    # ----- Report Table -----
    st.subheader("📊 รายงานข้อมูลการตรวจสอบ")
    filter_date = st.date_input("กรองตามวันที่", value=None)
    filter_status = st.selectbox("กรองตามสถานะ", ["ทั้งหมด", "งาน NG จากเครื่อง", "Rework", "Scrap"])

    filtered_df = report_df.copy()
    if filter_date:
        filtered_df = filtered_df[filtered_df["Timestamp"].str.contains(filter_date.strftime("%Y-%m-%d"))]
    if filter_status != "ทั้งหมด":
        filtered_df = filtered_df[filtered_df["Status"] == filter_status]

    st.dataframe(filtered_df, use_container_width=True)

    # ----- Pie Chart -----
    st.subheader("📈 สัดส่วนงาน Scrap เทียบ Rework")
    pie_data = report_df[report_df["Status"].isin(["Scrap", "Rework"])]["Status"].value_counts()
    fig, ax = plt.subplots()
    ax.pie(pie_data, labels=pie_data.index, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    st.pyplot(fig)

    # ----- Download Button -----
    to_download = BytesIO()
    report_df.to_excel(to_download, index=False, engine='openpyxl')
    st.download_button("📥 ดาวน์โหลดรายงานเป็น Excel", data=to_download.getvalue(), file_name="sorting_report.xlsx")
else:
    st.warning("⚠️ กรุณาอัปโหลดไฟล์รายชื่อพนักงาน และ รหัสงานทางแถบด้านซ้ายก่อนเริ่มใช้งาน")
