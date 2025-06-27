import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# กำหนดการเชื่อมต่อ Google Sheets
google_credentials = st.secrets["google_service_account"]
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_credentials, scope)
client = gspread.authorize(creds)

# ใช้ Spreadsheet ID
spreadsheet_id = '1GbHXO0d2GNXEwEZfeygGqNEBRQJQUoC_MO1mA-389gE'  # ใส่ Spreadsheet ID ของคุณที่นี่
sheet = client.open_by_key(spreadsheet_id).worksheet('Jobs')  # เชื่อมต่อกับชีท Jobs

# ฟังก์ชันสำหรับการเพิ่ม Timestamp
def add_status_timestamp(row_data, status_column_index, status_value):
    timestamp = datetime.now().strftime('%d-%m-%Y %H:%M')
    row_data[status_column_index] = status_value
    row_data[status_column_index + 1] = timestamp  # เพิ่ม Timestamp ถัดจากสถานะ
    return row_data

# ฟังก์ชันการทำงาน Forming
def forming_mode():
    st.header("Forming Mode (FM)")

    # การรับข้อมูลจากผู้ใช้
    department_from = 'Forming'  # เนื่องจาก Forming เป็นแผนกต้นทาง
    department_to = st.selectbox('เลือกแผนกปลายทาง', ['Tapping', 'Final Inspection', 'Out Source'])
    woc_number = st.text_input("หมายเลข WOC")
    part_name = st.selectbox("รหัสงาน / Part Name", ["Part A", "Part B", "Part C"])
    lot_number = st.text_input("หมายเลข LOT")
    total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
    barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
    sample_weight = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1)

    # คำนวณ Pieces Count
    pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000) if total_weight and barrel_weight and sample_weight and sample_count else 0

    if st.button("บันทึก"):
        row_data = [woc_number, part_name, "Employee Name", department_from, department_to, lot_number, total_weight, barrel_weight, sample_weight, sample_count, pieces_count, "", ""]
        row_data = add_status_timestamp(row_data, 11, "WIP-Forming")  # บันทึกสถานะและ Timestamp
        sheet.append_row(row_data)  # บันทึกลง Google Sheets
        st.success("บันทึกข้อมูลสำเร็จ!")

# ฟังก์ชันการทำงาน Tapping
def tapping_mode():
    st.header("Tapping Mode (TP)")

    # เลือก WOC จากข้อมูลที่มีอยู่ใน Google Sheets
    job_data = sheet.get_all_records()
    woc_numbers = [job['WOC Number'] for job in job_data]

    woc_number = st.selectbox("เลือกหมายเลข WOC", woc_numbers)
    part_name = st.selectbox("รหัสงาน / Part Name", ["Part A", "Part B", "Part C"])
    total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
    barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
    sample_weight = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1)

    if st.button("บันทึก"):
        pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000) if total_weight and barrel_weight and sample_weight and sample_count else 0
        row_data = [woc_number, part_name, "Employee Name", "Tapping", "Final Inspection", "LOT123", total_weight, barrel_weight, sample_weight, sample_count, pieces_count, "", ""]
        row_data = add_status_timestamp(row_data, 11, "WIP-Tapping")  # บันทึกสถานะและ Timestamp
        sheet.append_row(row_data)  # บันทึกลง Google Sheets
        st.success("บันทึกข้อมูลสำเร็จ!")

# ฟังก์ชันการทำงาน Final Inspection
def final_inspection_mode():
    st.header("Final Inspection Mode (FI)")

    # เลือก WOC จากข้อมูลที่มีอยู่ใน Google Sheets
    job_data = sheet.get_all_records()
    woc_numbers = [job['WOC Number'] for job in job_data]

    woc_number = st.selectbox("เลือกหมายเลข WOC", woc_numbers)
    part_name = st.selectbox("รหัสงาน / Part Name", ["Part A", "Part B", "Part C"])
    total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
    barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
    sample_weight = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1)

    if st.button("บันทึก"):
        pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000) if total_weight and barrel_weight and sample_weight and sample_count else 0
        row_data = [woc_number, part_name, "Employee Name", "Final Inspection", "Completed", "LOT456", total_weight, barrel_weight, sample_weight, sample_count, pieces_count, "", ""]
        row_data = add_status_timestamp(row_data, 11, "WIP-Final Inspection")  # บันทึกสถานะและ Timestamp
        sheet.append_row(row_data)  # บันทึกลง Google Sheets
        st.success("บันทึกข้อมูลสำเร็จ!")

# ฟังก์ชันหลัก
def main():
    st.title("ระบบรับส่งงานระหว่างแผนกในโรงงาน")

    mode = st.sidebar.selectbox("เลือกโหมด", ["Forming Mode", "Tapping Mode", "Final Inspection Mode"])

    if mode == "Forming Mode":
        forming_mode()
    elif mode == "Tapping Mode":
        tapping_mode()
    elif mode == "Final Inspection Mode":
        final_inspection_mode()

if __name__ == "__main__":
    main()
