import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Sorting Rework Process", layout="wide")

# ฟังก์ชันโหลดไฟล์ที่ผู้ใช้อัปโหลด
@st.cache_data
def load_excel(uploaded_file):
    if uploaded_file is not None:
        return pd.read_excel(uploaded_file)
    return pd.DataFrame()

st.sidebar.header("📁 อัปโหลดไฟล์อ้างอิง")

# ให้ผู้ใช้อัปโหลด 2 ไฟล์
employee_file = st.sidebar.file_uploader("📋 รายชื่อพนักงานแผนก Final Inspection", type=["xlsx"])
part_file = st.sidebar.file_uploader("🧾 รายการรหัสงาน (SCS)", type=["xlsx"])

# โหลดข้อมูลจากไฟล์
df_employee = load_excel(employee_file)
df_parts = load_excel(part_file)

# ตรวจสอบว่ามีข้อมูลหรือไม่
if df_employee.empty or df_parts.empty:
    st.warning("⚠️ กรุณาอัปโหลดไฟล์ Excel ทั้งสองไฟล์ในแถบด้านซ้ายก่อนใช้งาน")
    st.stop()

# สมมุติว่า column ชื่ออยู่ในคอลัมน์แรก
employee_names = df_employee.iloc[:, 0].dropna().unique().tolist()
part_codes = df_parts.iloc[:, 0].dropna().unique().tolist()

# ส่วนฟอร์มกรอกข้อมูล
st.title("📦 ฟอร์มบันทึกงาน Sorting Rework Process")

with st.form("data_entry"):
    st.subheader("🔍 บันทึกผลการตรวจสอบ")
    
    name = st.selectbox("👷‍♀️ ชื่อพนักงาน", employee_names)
    part_code = st.selectbox("🆔 รหัสงาน", part_codes)
    custom_code = st.text_input("🔤 หรือพิมพ์รหัสงานเอง (ถ้ามี)", "")
    part_code = custom_code if custom_code else part_code

    qty_total = st.number_input("✅ จำนวนที่ตรวจ", min_value=0, step=1)
    qty_ng = st.number_input("❌ จำนวน NG", min_value=0, step=1)
    qty_unchecked = st.number_input("🕒 จำนวนที่ยังไม่ตรวจ (Un-Test)", min_value=0, step=1)
    status = st.radio("📌 สถานะ", ["Rework", "Scrap"])

    submitted = st.form_submit_button("✅ บันทึกข้อมูล")

    if submitted:
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        st.success(f"✅ บันทึกสำเร็จ: {name} - {part_code} ({status}) เวลา {timestamp}")
        # ที่นี่คุณสามารถเพิ่มโค้ดบันทึกลง DataFrame หรือ Google Sheet ได้

