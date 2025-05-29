import streamlit as st
import pandas as pd
import os
import datetime
from io import BytesIO
from PIL import Image

st.set_page_config(page_title="Sorting Rework Process", layout="wide")

# ---------- Paths ----------
DATA_PATH = "/mnt/data/sorting_data.xlsx"
EMP_PATH = "/mnt/data/employees.xlsx"
PART_PATH = "/mnt/data/parts.xlsx"
IMAGE_FOLDER = "/mnt/data/uploaded_images"

os.makedirs(IMAGE_FOLDER, exist_ok=True)

# ---------- Helper Functions ----------
@st.cache_data
def load_master_data():
    if os.path.exists(EMP_PATH):
        df_emp = pd.read_excel(EMP_PATH)
    else:
        df_emp = pd.DataFrame()
    if os.path.exists(PART_PATH):
        df_part = pd.read_excel(PART_PATH)
    else:
        df_part = pd.DataFrame()
    return df_emp, df_part

def save_master_data(file, save_path):
    with open(save_path, "wb") as f:
        f.write(file.getbuffer())

def generate_job_id():
    today = datetime.datetime.now()
    prefix = today.strftime("%y%m")
    if os.path.exists(DATA_PATH):
        df = pd.read_excel(DATA_PATH)
        df = df[df['Job ID'].astype(str).str.startswith(prefix)]
        last_seq = max([int(str(jid)[-4:]) for jid in df['Job ID']]) if not df.empty else 0
    else:
        last_seq = 0
    return f"{prefix}{last_seq + 1:04d}"

def save_data(new_data):
    if os.path.exists(DATA_PATH):
        df = pd.read_excel(DATA_PATH)
        df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
    else:
        df = pd.DataFrame([new_data])
    df.to_excel(DATA_PATH, index=False)

# ---------- Load Data ----------
df_emp, df_part = load_master_data()
employees = df_emp['ชื่อ'].dropna().unique().tolist() if 'ชื่อ' in df_emp.columns else []
part_codes = df_part['รหัส'].dropna().unique().tolist() if 'รหัส' in df_part.columns else []

# ---------- Sidebar ----------
st.sidebar.title("🔧 เมนู")
mode = st.sidebar.selectbox("เลือกโหมด", ["Sorting MC", "Waiting Judgement", "Oil Cleaning", "อัปโหลด Master Data", "ดูรายงาน"])

# ---------- Upload Master Data ----------
if mode == "อัปโหลด Master Data":
    password = st.sidebar.text_input("🔐 กรุณาใส่รหัส", type="password")
    if password == "Sup":
        st.subheader("📤 อัปโหลดรายชื่อพนักงาน")
        emp_upload = st.file_uploader("อัปโหลดไฟล์รายชื่อ", type=["xlsx"])
        if emp_upload:
            save_master_data(emp_upload, EMP_PATH)
            st.success("✅ บันทึกรายชื่อสำเร็จ")

        st.subheader("📤 อัปโหลดรหัสงาน")
        part_upload = st.file_uploader("อัปโหลดไฟล์รหัสงาน", type=["xlsx"])
        if part_upload:
            save_master_data(part_upload, PART_PATH)
            st.success("✅ บันทึกรหัสงานสำเร็จ")

# ---------- Sorting MC ----------
elif mode == "Sorting MC":
    st.header("📦 บันทึกข้อมูล Sorting")
    with st.form("sorting_form"):
        job_id = generate_job_id()
        st.write(f"🆔 Job ID: `{job_id}`")

        date = st.date_input("📅 วันที่", value=datetime.date.today())
        employee = st.selectbox("👷‍♂️ พนักงาน", employees)
        part_code = st.selectbox("🔩 รหัสงาน", part_codes)
        qty_ng = st.number_input("❌ จำนวน NG", min_value=0)
        qty_pending = st.number_input("⏳ จำนวนที่ยังไม่ตรวจ", min_value=0)
        qty_total = qty_ng + qty_pending

        image = st.file_uploader("📸 อัปโหลดรูปภาพ", type=["jpg", "jpeg", "png"])

        submitted = st.form_submit_button("✅ บันทึกข้อมูล")
        if submitted:
            new_data = {
                "Job ID": job_id,
                "วันที่": date,
                "พนักงาน": employee,
                "รหัสงาน": part_code,
                "NG": qty_ng,
                "ยังไม่ตรวจ": qty_pending,
                "จำนวนทั้งหมด": qty_total,
                "สถานะ": "Sorting MC",
            }
            save_data(new_data)

            if image:
                img_path = os.path.join(IMAGE_FOLDER, f"{job_id}.png")
                img = Image.open(image)
                img.save(img_path)

            st.success(f"✅ บันทึกข้อมูลสำเร็จสำหรับ Job ID: {job_id}")

# ---------- Waiting Judgement ----------
elif mode == "Waiting Judgement":
    st.header("🧾 ตรวจสอบงาน (Judgement)")
    pw = st.text_input("🔐 กรุณาใส่รหัส", type="password")
    if pw == "Admin1":
        if os.path.exists(DATA_PATH):
            df = pd.read_excel(DATA_PATH)
            waiting = df[df['สถานะ'] == "Sorting MC"]
            for idx, row in waiting.iterrows():
                st.markdown(f"### 🆔 Job ID: {row['Job ID']}")
                st.write(f"👷‍♂️ พนักงาน: {row['พนักงาน']} | 🔩 รหัส: {row['รหัสงาน']} | ❌ NG: {row['NG']} | ⏳ ยังไม่ตรวจ: {row['ยังไม่ตรวจ']}")
                col1, col2 = st.columns(2)
                if col1.button("💥 Scrap", key=f"scrap_{idx}"):
                    df.at[idx, 'สถานะ'] = "Scrap"
                    df.to_excel(DATA_PATH, index=False)
                    st.success("✅ งานถูกบันทึกเป็น Scrap แล้ว")
                if col2.button("🔁 Rework", key=f"rework_{idx}"):
                    df.at[idx, 'สถานะ'] = "Oil Cleaning"
                    df.to_excel(DATA_PATH, index=False)
                    st.success("✅ งานถูกส่งไป Oil Cleaning แล้ว")
        else:
            st.info("ℹ️ ยังไม่มีข้อมูลให้ตรวจสอบ")

# ---------- Oil Cleaning ----------
elif mode == "Oil Cleaning":
    st.header("🧼 ล้างงาน (Oil Cleaning)")
    if os.path.exists(DATA_PATH):
        df = pd.read_excel(DATA_PATH)
        oil_jobs = df[df['สถานะ'] == "Oil Cleaning"]
        for idx, row in oil_jobs.iterrows():
            st.markdown(f"### 🆔 Job ID: {row['Job ID']} - 🔩 {row['รหัสงาน']}")
            if st.button("✅ ล้างเสร็จแล้ว", key=f"lavage_{idx}"):
                df.at[idx, 'สถานะ'] = "Lavage"
                df.to_excel(DATA_PATH, index=False)
                st.success("✅ บันทึกสถานะเป็นล้างเสร็จแล้ว")

# ---------- Report ----------
elif mode == "ดูรายงาน":
    st.header("📊 รายงานสรุป")
    if os.path.exists(DATA_PATH):
        df = pd.read_excel(DATA_PATH)
        st.dataframe(df)

        # Filter
        filter_mode = st.selectbox("🗓️ ดูข้อมูลตาม", ["รายวัน", "รายสัปดาห์", "รายเดือน", "รายปี"])
        today = datetime.date.today()
        if filter_mode == "รายวัน":
            df = df[df["วันที่"] == pd.to_datetime(today)]
        elif filter_mode == "รายสัปดาห์":
            week_ago = today - datetime.timedelta(days=7)
            df = df[(df["วันที่"] >= pd.to_datetime(week_ago)) & (df["วันที่"] <= pd.to_datetime(today))]
        elif filter_mode == "รายเดือน":
            df = df[df["วันที่"].dt.month == today.month]
        elif filter_mode == "รายปี":
            df = df[df["วันที่"].dt.year == today.year]

        # WIP
        st.subheader("📦 งานระหว่างกระบวนการ (WIP)")
        for step in ["Sorting MC", "Oil Cleaning"]:
            wip_df = df[df['สถานะ'] == step]
            total_qty = wip_df["จำนวนทั้งหมด"].sum()
            st.write(f"{step}: {len(wip_df)} รายการ | รวม: {total_qty} ชิ้น")

        # Scrap Summary
        st.subheader("🗑️ สรุป Scrap รายรหัสงาน")
        scrap = df[df["สถานะ"] == "Scrap"]
        if not scrap.empty:
            scrap_summary = scrap.groupby("รหัสงาน")["จำนวนทั้งหมด"].sum().reset_index()
            st.dataframe(scrap_summary)
    else:
        st.info("ℹ️ ยังไม่มีข้อมูลบันทึก")
