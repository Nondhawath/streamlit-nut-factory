import streamlit as st
import pandas as pd
import datetime
import os

# ------------------ CONFIG ------------------
EMP_PATH = "employee_list.xlsx"
PART_PATH = "part_code_list.xlsx"
REPORT_PATH = "sorting_report.xlsx"
JUDGEMENT_PASSWORD = "Admin1"

st.set_page_config(page_title="Sorting Process", layout="wide")

# ------------------ LOAD MASTER FILES ------------------
@st.cache_data
def load_excel_file(path):
    if os.path.exists(path):
        return pd.read_excel(path)
    return pd.DataFrame()

employee_df = load_excel_file(EMP_PATH)
part_df = load_excel_file(PART_PATH)

# ------------------ UPLOAD MASTER ------------------
with st.sidebar.expander("📤 อัปโหลดไฟล์พนักงานและรหัสงาน"):
    emp_upload = st.file_uploader("อัปโหลดรายชื่อพนักงาน", type="xlsx")
    if emp_upload:
        employee_df = pd.read_excel(emp_upload)
        employee_df.to_excel(EMP_PATH, index=False)
        st.success("อัปเดตรายชื่อพนักงานเรียบร้อยแล้ว ✅")

    part_upload = st.file_uploader("อัปโหลดรหัสงาน", type="xlsx")
    if part_upload:
        part_df = pd.read_excel(part_upload)
        part_df.to_excel(PART_PATH, index=False)
        st.success("อัปเดตรหัสงานเรียบร้อยแล้ว ✅")

employees = employee_df['ชื่อ'].dropna().unique().tolist() if 'ชื่อ' in employee_df.columns else []
part_codes = part_df['รหัส'].dropna().unique().tolist() if 'รหัส' in part_df.columns else []

# ------------------ LOAD REPORT ------------------
def load_report():
    if os.path.exists(REPORT_PATH):
        return pd.read_excel(REPORT_PATH)
    return pd.DataFrame()

def save_report(df):
    df.to_excel(REPORT_PATH, index=False)

report_df = load_report()

# ------------------ Job ID Generator ------------------
def generate_job_id():
    now = datetime.datetime.now()
    prefix = now.strftime("%y%m")
    if 'Job ID' in report_df.columns:
        existing = report_df[report_df['Job ID'].astype(str).str.startswith(prefix)]
        last_seq = max([int(str(jid)[-4:]) for jid in existing['Job ID']]) if not existing.empty else 0
    else:
        last_seq = 0
    return f"{prefix}{last_seq+1:04d}"

# ------------------ MODE SELECTION ------------------
mode = st.selectbox("เลือกโหมดการทำงาน", ["📦 Sorting MC", "⚖️ Waiting Judgement", "🧼 Oil Cleaning", "📊 WIP รายงาน"])

# ------------------ SORTING MODE ------------------
if mode == "📦 Sorting MC":
    st.header("📦 กรอกข้อมูลงาน Sorting MC")
    with st.form("sorting_form"):
        operator = st.selectbox("👩‍🏭 ชื่อผู้ตรวจสอบ", employees)
        part_code = st.selectbox("🔢 รหัสงาน", part_codes)
        qty_checked = st.number_input("✅ จำนวนที่ตรวจแล้ว", min_value=0)
        qty_ng = st.number_input("❌ จำนวน NG", min_value=0)
        qty_pending = st.number_input("⏳ จำนวนที่ยังไม่ตรวจ", min_value=0)
        status = st.radio("📌 สถานะ", ["Waiting Judgement"])
        submit = st.form_submit_button("💾 บันทึกข้อมูล")

        if submit:
            job_id = generate_job_id()
            new_data = {
                "Job ID": job_id,
                "วันที่": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "ชื่อผู้ตรวจสอบ": operator,
                "รหัสงาน": part_code,
                "จำนวนที่ตรวจ": qty_checked,
                "จำนวน NG": qty_ng,
                "จำนวนที่ยังไม่ตรวจ": qty_pending,
                "สถานะ": status
            }
            report_df = pd.concat([report_df, pd.DataFrame([new_data])], ignore_index=True)
            save_report(report_df)
            st.success(f"บันทึกเรียบร้อยแล้ว 🎉 (Job ID: {job_id})")

# ------------------ JUDGEMENT MODE ------------------
elif mode == "⚖️ Waiting Judgement":
    st.header("⚖️ ตรวจสอบสถานะ NG")
    password = st.text_input("🔐 กรุณาใส่รหัสเพื่อเข้าใช้งาน", type="password")
    if password == JUDGEMENT_PASSWORD:
        waiting_jobs = report_df[report_df['สถานะ'] == "Waiting Judgement"]
        for i, row in waiting_jobs.iterrows():
            st.markdown(f"### 🔎 Job ID: {row['Job ID']} - รหัสงาน: {row['รหัสงาน']} - จำนวน NG: {row['จำนวน NG']}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"🛠 Rework - {row['Job ID']}"):
                    report_df.at[i, "สถานะ"] = "Oil Cleaning"
                    save_report(report_df)
                    st.success(f"เปลี่ยนสถานะ Job ID {row['Job ID']} เป็น Rework แล้ว")
                    st.experimental_rerun()
            with col2:
                if st.button(f"🗑 Scrap - {row['Job ID']}"):
                    report_df.at[i, "สถานะ"] = "Scrap"
                    save_report(report_df)
                    st.success(f"เปลี่ยนสถานะ Job ID {row['Job ID']} เป็น Scrap แล้ว")
                    st.experimental_rerun()
    else:
        st.warning("กรุณาใส่รหัสผ่านเพื่อเข้าใช้งาน Judgement")

# ------------------ OIL CLEANING MODE ------------------
elif mode == "🧼 Oil Cleaning":
    st.header("🧼 งานที่ต้องทำความสะอาด")
    cleaning_jobs = report_df[report_df['สถานะ'] == "Oil Cleaning"]
    for i, row in cleaning_jobs.iterrows():
        st.markdown(f"### 🧴 Job ID: {row['Job ID']} - รหัสงาน: {row['รหัสงาน']} - จำนวน NG: {row['จำนวน NG']}")
        if st.button(f"✅ ล้างเสร็จแล้ว - {row['Job ID']}"):
            report_df.at[i, "สถานะ"] = "Lavage Done"
            save_report(report_df)
            st.success(f"เปลี่ยนสถานะ Job ID {row['Job ID']} เป็น Lavage Done แล้ว")
            st.experimental_rerun()

# ------------------ WIP MODE ------------------
elif mode == "📊 WIP รายงาน":
    st.header("📊 รายงานสถานะงานคงค้าง (WIP)")
    wip = report_df[report_df['สถานะ'].isin(["Waiting Judgement", "Oil Cleaning"])]
    st.dataframe(wip)
    st.download_button("📥 ดาวน์โหลดรายงาน WIP", data=wip.to_csv(index=False), file_name="WIP_report.csv")
