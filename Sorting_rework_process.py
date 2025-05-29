import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import os

st.set_page_config(page_title="Sorting Process App", layout="wide")

DATA_FILE = "sorting_report_updated.xlsx"
EMP_FILE = "รายชื่อพนักงานแผนก Final Inspection.xlsx"
PART_FILE = "Master list SCS part name.xlsx"

# ----- File Upload for Employee & Part Code -----
st.sidebar.header("📂 อัปโหลดข้อมูลพื้นฐาน")
uploaded_emp_file = st.sidebar.file_uploader("อัปโหลดรายชื่อพนักงาน (xlsx)", type=["xlsx"], key="emp")
uploaded_part_file = st.sidebar.file_uploader("อัปโหลดรหัสงาน (xlsx)", type=["xlsx"], key="part")

if uploaded_emp_file:
    with open(EMP_FILE, "wb") as f:
        f.write(uploaded_emp_file.read())
    st.sidebar.success("✅ อัปโหลดรายชื่อพนักงานเรียบร้อยแล้ว")

if uploaded_part_file:
    with open(PART_FILE, "wb") as f:
        f.write(uploaded_part_file.read())
    st.sidebar.success("✅ อัปโหลดรหัสงานเรียบร้อยแล้ว")

# ----- Load Employee & Part Code Data -----
@st.cache_data
def load_data():
    df_emp = pd.read_excel(EMP_FILE)
    df_part = pd.read_excel(PART_FILE)
    return df_emp, df_part

try:
    df_emp, df_part = load_data()
    employees = df_emp['ชื่อ'].dropna().unique().tolist()
    leaders = df_emp[df_emp['ตำแหน่ง'].str.contains("Leader", na=False)]['ชื่อ'].unique().tolist()
    part_codes = df_part['รหัส'].dropna().unique().tolist()
except Exception as e:
    st.error(f"❌ ไม่สามารถโหลดข้อมูลรายชื่อพนักงานหรือรหัสงานได้: {e}")
    st.stop()

# ----- Load Existing Report or Create New -----
def load_report():
    if os.path.exists(DATA_FILE):
        return pd.read_excel(DATA_FILE)
    else:
        columns = [
            "Job ID", "Timestamp", "Employee", "Part Code", "Total Checked", "NG", "Un-Tested", "Status",
            "Current Process", "Rework Time", "Leader", "Oil Cleaning Time", "Sender", "Judged By"
        ]
        return pd.DataFrame(columns=columns)

report_df = load_report()

# ----- Generate Job ID -----
def generate_job_id(df):
    now = datetime.now()
    yymm = now.strftime("%y%m")
    this_month_jobs = df[df['Job ID'].astype(str).str.startswith(yymm)]
    next_num = len(this_month_jobs) + 1
    return f"{yymm}{next_num:04d}"

# ----- Mode Selector -----
st.sidebar.title("🛠️ เลือกโหมดการทำงาน")
mode = st.sidebar.selectbox("เลือกโหมด", ["Sorting MC", "Waiting Judgement", "Oil Cleaning"])

if mode == "Sorting MC":
    st.header("📋 กรอกข้อมูลผลการตรวจสอบจากแผนก Sorting")
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
        submitted = st.form_submit_button("✅ บันทึกข้อมูล")
        if submitted:
            job_id = generate_job_id(report_df)
            new_data = pd.DataFrame([{
                "Job ID": job_id,
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Employee": employee,
                "Part Code": part_code,
                "Total Checked": total_checked,
                "NG": ng,
                "Un-Tested": untested,
                "Status": status,
                "Current Process": "Waiting Judgement" if status in ["Rework", "Scrap"] else "Sorting",
                "Rework Time": "",
                "Leader": "",
                "Oil Cleaning Time": "",
                "Sender": "",
                "Judged By": ""
            }])
            report_df = pd.concat([report_df, new_data], ignore_index=True)
            report_df.to_excel(DATA_FILE, index=False)
            st.success(f"✅ บันทึกข้อมูล Job ID: {job_id} เรียบร้อยแล้ว")

elif mode == "Waiting Judgement":
    st.header("🧾 รายการงานที่รอ Judgement")
    waiting_df = report_df[(report_df['Current Process'] == "Waiting Judgement") & (report_df['Status'].isin(["Rework", "Scrap"]) == False)]
    st.dataframe(waiting_df, use_container_width=True)

    job_ids = waiting_df['Job ID'].tolist()
    selected_job_id = st.selectbox("เลือก Job ID", job_ids)
    judged_by = st.selectbox("ผู้ตัดสินใจ (Judgement)", leaders)

    if st.button("📛 Scrap"):
        report_df.loc[report_df['Job ID'] == selected_job_id, ['Status', 'Current Process', 'Judged By']] = ["Scrap", "Done", judged_by]
        report_df.to_excel(DATA_FILE, index=False)
        st.success(f"🚮 บันทึก Scrap สำหรับ Job ID {selected_job_id}")

    if st.button("🔁 Rework"):
        report_df.loc[report_df['Job ID'] == selected_job_id, ['Status', 'Current Process', 'Rework Time', 'Leader', 'Judged By']] = [
            "Rework", "Oil Cleaning", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), judged_by, judged_by
        ]
        report_df.to_excel(DATA_FILE, index=False)
        st.success(f"🔁 ส่งงาน Rework สำหรับ Job ID {selected_job_id}")

elif mode == "Oil Cleaning":
    st.header("🧼 รายการงานที่รอการล้าง")
    cleaning_df = report_df[report_df['Current Process'] == "Oil Cleaning"]
    st.dataframe(cleaning_df, use_container_width=True)

    job_ids = cleaning_df['Job ID'].tolist()
    selected_job_id = st.selectbox("เลือก Job ID เพื่อบันทึกว่าล้างเสร็จแล้ว", job_ids)
    sender = st.selectbox("ผู้ส่งกลับไป Sorting", employees)

    if st.button("🧴 ล้างเสร็จแล้ว"):
        report_df.loc[report_df['Job ID'] == selected_job_id, ['Current Process', 'Oil Cleaning Time', 'Sender']] = [
            "Sorting", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), sender
        ]
        report_df.to_excel(DATA_FILE, index=False)
        st.success(f"✅ ล้างเสร็จแล้วสำหรับ Job ID {selected_job_id}")

# ----- WIP Summary -----
st.subheader("📦 งานระหว่างกระบวนการ (WIP)")
for process in ["Sorting", "Waiting Judgement", "Oil Cleaning"]:
    count = report_df[report_df['Current Process'] == process].shape[0]
    st.metric(label=f"{process}", value=f"{count} งาน")

# ----- Pie Chart -----
st.subheader("📊 สัดส่วนงาน Scrap / Rework / ปกติ")
status_counts = report_df['Status'].value_counts()
fig, ax = plt.subplots()
ax.pie(status_counts, labels=status_counts.index, autopct='%1.1f%%', startangle=90)
ax.axis('equal')
st.pyplot(fig)

# ----- Download -----
st.download_button("📥 ดาวน์โหลดรายงาน Excel", data=report_df.to_excel(index=False), file_name="sorting_report_updated.xlsx")
