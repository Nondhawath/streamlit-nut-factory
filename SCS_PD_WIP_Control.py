import streamlit as st
from datetime import datetime

# ฟังก์ชันคำนวณ Pieces Count
def calculate_pieces_count(total_weight, barrel_weight, sample_weight, sample_count):
    return (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)

# ฟังก์ชันบันทึกข้อมูลลงใน Google Sheets
def log_to_google_sheets(data):
    # ใส่โค้ดการบันทึกลง Google Sheets ที่นี่
    pass

# Streamlit UI
st.title("Work Order Management System")

# ฟอร์มกรอกข้อมูลสำหรับการโอนงานจาก FM ไป TP
st.header("Forming (FM) to Tapping (TP) Transfer")

# เลือกแผนกที่ทำการโอนงาน (FM หรือ TP)
department_from = st.selectbox("Select Department From", ["Forming (FM)", "Tapping (TP)"])

# ฟอร์มการกรอกข้อมูลสำหรับ FM (แผนกต้นทาง)
if department_from == "Forming (FM)":
    # เมื่อแผนกต้นทางเป็น FM จะไม่มี WOC ก่อนหน้า
    new_woc = st.text_input("Enter New WOC Number")
    previous_woc = "N/A"  # ไม่มี WOC ก่อนหน้า
else:
    # เมื่อแผนกต้นทางเป็น TP จะสามารถเลือก WOC ก่อนหน้าได้
    previous_woc = st.selectbox("Select Previous WOC", ["WOC001", "WOC002", "WOC003"])  # ตัวอย่าง WOC ก่อนหน้า
    new_woc = st.text_input("Enter New WOC Number")

# กรอกข้อมูลการชั่งน้ำหนัก
lot_number = st.text_input("Lot Number")
total_weight = st.number_input("Total Weight", min_value=0.0)
barrel_weight = st.number_input("Barrel Weight", min_value=0.0)
sample_weight = st.number_input("Sample Weight", min_value=0.0)
sample_count = st.number_input("Sample Count", min_value=0)

# คำนวณ Pieces Count
if total_weight and barrel_weight and sample_weight and sample_count:
    pieces_count = calculate_pieces_count(total_weight, barrel_weight, sample_weight, sample_count)
    st.write(f"Pieces Count: {pieces_count:.2f}")

# บันทึกข้อมูลเมื่อกดปุ่ม
if st.button("Save Data"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "Transfer"  # สถานะเป็น "Transfer"
    
    # ข้อมูลที่ต้องบันทึก
    data = [previous_woc, new_woc, lot_number, total_weight, barrel_weight, sample_weight, sample_count, pieces_count, status, timestamp]
    
    # บันทึกข้อมูลลง Google Sheets
    log_to_google_sheets(data)
    st.success("Data saved successfully. WOC Transfer completed.")
