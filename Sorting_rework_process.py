import streamlit as st
import pandas as pd
import os
from datetime import datetime
from io import BytesIO

# -------------------------
# CONFIG
# -------------------------
REPORT_FILE = "report_data.xlsx"
EMPLOYEE_FILE = "employee_master.xlsx"
PARTCODE_FILE = "partcode_master.xlsx"
IMAGE_FOLDER = "uploaded_images"
PASSWORD = "Admin1"

os.makedirs(IMAGE_FOLDER, exist_ok=True)

# -------------------------
# SESSION INITIALIZATION
# -------------------------
if "report_df" not in st.session_state:
    if os.path.exists(REPORT_FILE):
        st.session_state.report_df = pd.read_excel(REPORT_FILE)
    else:
        st.session_state.report_df = pd.DataFrame()

if "employee_df" not in st.session_state:
    if os.path.exists(EMPLOYEE_FILE):
        st.session_state.employee_df = pd.read_excel(EMPLOYEE_FILE)
    else:
        st.session_state.employee_df = pd.DataFrame()

if "partcode_df" not in st.session_state:
    if os.path.exists(PARTCODE_FILE):
        st.session_state.partcode_df = pd.read_excel(PARTCODE_FILE)
    else:
        st.session_state.partcode_df = pd.DataFrame()

# -------------------------
# HELPER FUNCTIONS
# -------------------------
def save_uploaded_master(uploaded_file, path):
    if uploaded_file:
        with open(path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return pd.read_excel(path)
    return pd.DataFrame()

def generate_job_id():
    now = datetime.now()
    prefix = now.strftime("%y%m")
    df = st.session_state.report_df
    existing = df[df['Job ID'].astype(str).str.startswith(prefix)] if not df.empty else pd.DataFrame()
    if existing.empty:
        return prefix + "0001"
    last_seq = max([int(str(jid)[-4:]) for jid in existing['Job ID'] if str(jid).isdigit()])
    return prefix + f"{last_seq + 1:04d}"

def save_uploaded_image(uploaded_file, job_id):
    if uploaded_file:
        ext = os.path.splitext(uploaded_file.name)[1]
        filename = os.path.join(IMAGE_FOLDER, f"{job_id}{ext}")
        with open(filename, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return filename
    return None

# -------------------------
# SIDEBAR
# -------------------------
st.sidebar.title("📂 อัปโหลดไฟล์ Master")
emp_upload = st.sidebar.file_uploader("📄 รายชื่อพนักงาน", type=[".xlsx"])
if emp_upload:
    st.session_state.employee_df = save_uploaded_master(emp_upload, EMPLOYEE_FILE)

part_upload = st.sidebar.file_uploader("📦 รหัสงาน", type=[".xlsx"])
if part_upload:
    st.session_state.partcode_df = save_uploaded_master(part_upload, PARTCODE_FILE)

mode = st.sidebar.selectbox("🔧 โหมด", ["Sorting MC", "Waiting Judgement", "Oil Cleaning", "📊 รายงาน WIP"])

# -------------------------
# MAIN LOGIC
# -------------------------
st.title(f"🧾 ระบบบันทึกข้อมูล - {mode}")

if mode == "Sorting MC":
    with st.form("sorting_form"):
        name = st.selectbox("👷‍♂️ ชื่อพนักงาน", st.session_state.employee_df['ชื่อ'].dropna().unique())
        part_code = st.selectbox("📦 รหัสงาน", st.session_state.partcode_df['รหัส'].dropna().unique())
        qty_ng = st.number_input("❌ จำนวน NG", min_value=0)
        qty_pending = st.number_input("⏳ จำนวนที่ยังไม่ตรวจ", min_value=0)
        status = st.selectbox("📌 สถานะ", ["รอตัดสินใจ"])
        image_file = st.file_uploader("📸 อัปโหลดรูปภาพ", type=[".jpg", ".png", ".jpeg"])

        submitted = st.form_submit_button("✅ บันทึก")
        if submitted:
            job_id = generate_job_id()
            qty_total = qty_ng + qty_pending
            image_path = save_uploaded_image(image_file, job_id)

            new_data = pd.DataFrame([{
                "วันที่": datetime.now().date(),
                "เวลา": datetime.now().strftime("%H:%M:%S"),
                "Job ID": job_id,
                "ชื่อพนักงาน": name,
                "รหัสงาน": part_code,
                "จำนวน NG": qty_ng,
                "จำนวนที่ยังไม่ตรวจ": qty_pending,
                "จำนวนทั้งหมด": qty_total,
                "สถานะ": status,
                "รูปภาพ": image_path or ""
            }])
            st.session_state.report_df = pd.concat([st.session_state.report_df, new_data], ignore_index=True)
            st.session_state.report_df.to_excel(REPORT_FILE, index=False)
            st.success(f"✅ บันทึกสำเร็จ Job ID: {job_id}")

elif mode == "Waiting Judgement":
    password = st.text_input("🔑 ใส่รหัสผ่านเพื่อเข้าโหมดนี้", type="password")
    if password == PASSWORD:
        df_pending = st.session_state.report_df[st.session_state.report_df['สถานะ'] == "รอตัดสินใจ"]
        for _, row in df_pending.iterrows():
            st.write(f"### Job ID: {row['Job ID']}, รหัสงาน: {row['รหัสงาน']}, จำนวน: {row['จำนวนทั้งหมด']}")
            if st.button(f"Scrap {row['Job ID']}"):
                st.session_state.report_df.loc[st.session_state.report_df['Job ID'] == row['Job ID'], 'สถานะ'] = "Scrap"
                st.session_state.report_df.to_excel(REPORT_FILE, index=False)
                st.experimental_rerun()
            if st.button(f"Rework {row['Job ID']}"):
                st.session_state.report_df.loc[st.session_state.report_df['Job ID'] == row['Job ID'], 'สถานะ'] = "Oil Cleaning"
                st.session_state.report_df.to_excel(REPORT_FILE, index=False)
                st.experimental_rerun()
    else:
        st.warning("กรุณาใส่รหัสผ่านให้ถูกต้อง")

elif mode == "Oil Cleaning":
    df_cleaning = st.session_state.report_df[st.session_state.report_df['สถานะ'] == "Oil Cleaning"]
    for _, row in df_cleaning.iterrows():
        st.write(f"### Job ID: {row['Job ID']}, รหัสงาน: {row['รหัสงาน']}, จำนวน: {row['จำนวนทั้งหมด']}")
        if st.button(f"ล้างเสร็จแล้ว {row['Job ID']}"):
            st.session_state.report_df.loc[st.session_state.report_df['Job ID'] == row['Job ID'], 'สถานะ'] = "ล้างเสร็จแล้ว"
            st.session_state.report_df.to_excel(REPORT_FILE, index=False)
            st.experimental_rerun()

elif mode == "📊 รายงาน WIP":
    st.subheader("📌 WIP ในแต่ละกระบวนการ")
    for step in ["รอตัดสินใจ", "Oil Cleaning"]:
        df_step = st.session_state.report_df[st.session_state.report_df['สถานะ'] == step]
        total = df_step['จำนวนทั้งหมด'].sum()
        st.write(f"🔹 {step}: {total} ชิ้น")

    st.subheader("📊 งาน Scrap")
    df_scrap = st.session_state.report_df[st.session_state.report_df['สถานะ'] == "Scrap"]
    scrap_summary = df_scrap.groupby('รหัสงาน')['จำนวนทั้งหมด'].sum().reset_index()
    st.dataframe(scrap_summary)

    with st.expander("🔎 ตัวกรองรายงาน"):
        date_option = st.selectbox("ช่วงเวลา", ["ทั้งหมด", "รายวัน", "รายสัปดาห์", "รายเดือน", "รายปี"])
        today = datetime.today()
        df = st.session_state.report_df.copy()

        if date_option == "รายวัน":
            df = df[df['วันที่'] == today.date()]
        elif date_option == "รายสัปดาห์":
            df = df[df['วันที่'] >= today - pd.Timedelta(days=7)]
        elif date_option == "รายเดือน":
            df = df[df['วันที่'].dt.month == today.month]
        elif date_option == "รายปี":
            df = df[df['วันที่'].dt.year == today.year]

        st.dataframe(df)

    towrite = BytesIO()
    st.session_state.report_df.to_excel(towrite, index=False)
    towrite.seek(0)
    st.download_button("📥 ดาวน์โหลดรายงาน Excel", towrite, file_name="sorting_report_updated.xlsx")
