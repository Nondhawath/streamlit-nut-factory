import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Setting up Google Sheets Connection
def get_google_credentials():
    # รับข้อมูลจาก secrets
    google_credentials = st.secrets["google_service_account"]
    # กำหนด scope ของ API ที่ต้องการ
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # เชื่อมต่อกับ Google Sheets API
    creds = ServiceAccountCredentials.from_json_keyfile_dict(google_credentials, scope)
    client = gspread.authorize(creds)
    return client

# ฟังก์ชันบันทึกข้อมูลสถานะใน Google Sheets
def add_status_timestamp(row_data, status_column_index, status_value):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    row_data[status_column_index] = status_value
    row_data[status_column_index + 1] = timestamp  # ใส่เวลาติดกับสถานะ
    return row_data

# โหมดการทำงาน Forming
def forming_mode(sheet):
    st.header("Forming Mode (FM)")

    # ข้อมูลต่างๆ ที่ต้องการจากผู้ใช้
    part_name = st.selectbox("รหัสงาน / Part Name", ["Part 1", "Part 2", "Part 3"])
    employee = st.selectbox("ชื่อพนักงาน", ["พนักงาน 1", "พนักงาน 2", "พนักงาน 3"])
    lot_number = st.text_input("หมายเลข LOT")
    total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
    barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
    sample_weight = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1)

    # คำนวณจำนวนชิ้นงาน
    pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)

    if st.button("บันทึก"):
        # ข้อมูลที่ต้องการบันทึกในแถว
        row_data = [part_name, employee, "Forming", "Tapping", lot_number, total_weight, barrel_weight, sample_weight, sample_count, pieces_count]
        row_data = add_status_timestamp(row_data, 10, "WIP-Forming")  # เพิ่มสถานะและเวลา
        sheet.append_row(row_data)  # เพิ่มแถวใหม่ในชีต
        st.success("บันทึกข้อมูลสำเร็จ!")

# โหมดการทำงาน Tapping
def tapping_mode(sheet):
    st.header("Tapping Mode (TP)")

    # ข้อมูลการรับงานจาก Forming
    job_data = sheet.get_all_records()
    job_woc = st.selectbox("เลือกหมายเลข WOC", [job['WOC Number'] for job in job_data])

    # ถ้ามีการเลือกหมายเลข WOC
    if job_woc:
        st.write(f"เลือกหมายเลข WOC: {job_woc}")
        total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
        barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
        sample_weight = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0)
        sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1)

        if total_weight and barrel_weight and sample_weight and sample_count:
            pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)
            st.write(f"จำนวนชิ้นงาน: {pieces_count:.2f}")

        if st.button("คำนวณและบันทึก"):
            row_data = [job_woc, pieces_count]
            row_data = add_status_timestamp(row_data, 1, "WIP-Tapping")  # เพิ่มสถานะ Tapping
            sheet.append_row(row_data)  # บันทึกข้อมูลลงใน Google Sheets
            st.success("ข้อมูล Tapping ถูกบันทึกแล้ว!")

# ฟังก์ชันหลักในการเลือกโหมด
def main():
    st.title("ระบบจัดการการรับส่งงานระหว่างแผนก")
    
    # เลือกโหมด
    mode = st.sidebar.selectbox("เลือกโหมด", ['Forming', 'Tapping', 'Final Inspection', 'Final Work', 'Transfer'])
    
    # เชื่อมต่อกับ Google Sheets
    client = get_google_credentials()
    sheet = client.open("SCS_PD_WIP_Control").sheet1  # ชื่อของไฟล์ Google Sheets ที่จะใช้
    
    if mode == 'Forming':
        forming_mode(sheet)
    elif mode == 'Tapping':
        tapping_mode(sheet)

if __name__ == "__main__":
    main()
