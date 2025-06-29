import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
import datetime

# ดึงข้อมูล Firebase Credentials จาก Secrets
firebase_credentials = st.secrets["firebase_credentials"]

# สร้างไฟล์ชั่วคราวจาก JSON ใน Secrets
cred = credentials.Certificate(firebase_credentials)

# เริ่มต้น Firebase Admin SDK
firebase_admin.initialize_app(cred)

# เข้าถึง Firestore
db = firestore.client()

# ฟังก์ชันเพื่อบันทึกข้อมูลการส่งงาน
def log_transfer_to_logs(woc_number, part_name, employee, department_from, department_to, lot_number, total_weight, barrel_weight, sample_weight, sample_count, pieces_count, status):
    transfer_ref = db.collection('transfer_logs')
    transfer_ref.add({
        "WOC Number": woc_number,
        "Part Name": part_name,
        "Employee": employee,
        "Department From": department_from,
        "Department To": department_to,
        "Lot Number": lot_number,
        "Total Weight": total_weight,
        "Barrel Weight": barrel_weight,
        "Sample Weight": sample_weight,
        "Sample Count": sample_count,
        "Pieces Count": pieces_count,
        "Status": status,
        "Timestamp": datetime.datetime.now(),
    })

# ฟังก์ชัน Forming Mode (แผนก Forming)
def forming_mode():
    st.header("Forming Mode")
    department_from = 'Forming'
    department_to = st.selectbox('เลือกแผนกปลายทาง', ['Tapping', 'Final Inspection'])
    
    woc_number = st.text_input("หมายเลข WOC")
    part_name = st.text_input("ชื่อรหัสงาน / Part Name")
    employee = st.text_input("ชื่อพนักงาน")
    lot_number = st.text_input("หมายเลข LOT")
    total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
    barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
    sample_weight = st.number_input("น้ำหนักของตัวอย่าง", min_value=0.0)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1)
    
    # คำนวณจำนวนชิ้นงาน
    if total_weight and barrel_weight and sample_weight and sample_count:
        pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)
        st.write(f"จำนวนชิ้นงาน: {pieces_count:.2f}")
    
    if st.button("บันทึกข้อมูล"):
        # เก็บข้อมูลการส่งงานจาก Forming
        log_transfer_to_logs(woc_number, part_name, employee, department_from, department_to, lot_number, total_weight, barrel_weight, sample_weight, sample_count, pieces_count, "WIP-Forming")
        st.success("บันทึกข้อมูลสำเร็จ!")

# ฟังก์ชัน Tapping Mode (แผนก Tapping)
def tapping_mode():
    st.header("Tapping Mode")
    woc_number = st.text_input("หมายเลข WOC")
    # ดึงข้อมูลจาก Firestore สำหรับงานที่รับมาจาก Forming
    transfer_logs_ref = db.collection('transfer_logs')
    query = transfer_logs_ref.where('WOC Number', '==', woc_number).stream()
    
    for doc in query:
        job_data = doc.to_dict()
        st.write(f"WOC Number: {job_data['WOC Number']}")
        st.write(f"Part Name: {job_data['Part Name']}")
        st.write(f"Employee: {job_data['Employee']}")
        st.write(f"Department From: {job_data['Department From']}")
        st.write(f"Department To: {job_data['Department To']}")
        st.write(f"Lot Number: {job_data['Lot Number']}")
        st.write(f"Total Weight: {job_data['Total Weight']}")
        st.write(f"Barrel Weight: {job_data['Barrel Weight']}")
        st.write(f"Sample Weight: {job_data['Sample Weight']}")
        st.write(f"Sample Count: {job_data['Sample Count']}")
        st.write(f"Pieces Count: {job_data['Pieces Count']}")
    
    # ตรวจสอบน้ำหนักและชิ้นงาน
    if st.button("บันทึกข้อมูล"):
        log_transfer_to_logs(woc_number, job_data['Part Name'], job_data['Employee'], 'Tapping', 'Final Inspection', job_data['Lot Number'], job_data['Total Weight'], job_data['Barrel Weight'], job_data['Sample Weight'], job_data['Sample Count'], job_data['Pieces Count'], "WIP-Tapping")
        st.success("บันทึกข้อมูลสำเร็จ!")

# ฟังก์ชันหลัก
def main():
    st.title("ระบบส่งงานระหว่างแผนก")
    mode = st.selectbox("เลือกโหมดการทำงาน", ['Forming', 'Tapping'])

    if mode == 'Forming':
        forming_mode()
    elif mode == 'Tapping':
        tapping_mode()

if __name__ == "__main__":
    main()
