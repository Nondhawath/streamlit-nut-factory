import streamlit as st 
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import io

st.set_page_config(page_title="Sorting Process App", layout="wide")

# ----- File Upload Instead of Hardcoded Filenames -----
st.header("📁 อัปโหลดข้อมูลพนักงานและรหัสงาน")
emp_file = st.file_uploader("📤 อัปโหลดไฟล์รายชื่อพนักงาน (Excel)", type=["xlsx"])
part_file = st.file_uploader("📤 อัปโหลดไฟล์รหัสงาน (Excel)", type=["xlsx"])

if emp_file and part_file:
    df_emp = pd.read_excel(emp_file)
    df_part = pd.read_excel(part_file)

    employees = df_emp['ชื่อ'].dropna().unique().tolist()
    leaders = df_emp[df_emp['ตำแหน่ง'].str.contains("Leader", na=False)]['ชื่อ'].unique().tolist()
    part_codes = df_part['รหัส'].dropna().unique().tolist()

    # ----- Load Existing Report or Create New -----
    DATA_FILE = "sorting_report_updated.xlsx"

    def load_report():
        try:
            return pd.read_excel(DATA_FILE)
        except:
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
                rework = st.checkbox("📤 ส่งงานไปแผนก Oil Cleaning")
                if rework:
                    rework_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if status == "Rework" and st.checkbox("📤 ส่งงานกลับไป Sorting"):
                oil_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sender = st.selectbox("ชื่อผู้ส่งกลับ", employees, key="sender_select")

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
    pie_df = report_df[report_df['Status'].isin(["Scrap", "Rework"])]
    if not pie_df.empty:
        status_counts = pie_df["Status"].value_counts()
        fig, ax = plt.subplots()
        ax.pie(status_counts, labels=status_counts.index, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')
        st.pyplot(fig)
    else:
        st.info("ไม่มีข้อมูล Scrap หรือ Rework สำหรับแสดงกราฟ")

    # ----- Download Button -----
    st.download_button(
        "📥 ดาวน์โหลดรายงานเป็น Excel", 
        data=report_df.to_excel(index=False, engine='openpyxl'), 
        file_name="sorting_report.xlsx"
    )
else:
    st.warning("กรุณาอัปโหลดไฟล์พนักงานและรหัสงานก่อนเริ่มใช้งาน")
