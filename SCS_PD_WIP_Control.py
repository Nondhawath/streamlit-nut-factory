import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# กำหนด Google Sheets API credentials
google_credentials = st.secrets["google_service_account"]  
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_credentials, scope)
client = gspread.authorize(creds)

spreadsheet_id = '1GbHXO0d2GNXEwEZfeygGqNEBRQJQUoC_MO1mA-389gE'  # ใส่ Spreadsheet ID ที่ใช้งานจริง
sheet = client.open_by_key(spreadsheet_id).worksheet('Jobs')  # "Jobs" sheet
# ถ้ามีหลายชีทเชื่อมต่อเพิ่ม
part_code_master_sheet = client.open_by_key(spreadsheet_id).worksheet('part_code_master')
employees_sheet = client.open_by_key(spreadsheet_id).worksheet('Employees')
machines_sheet = client.open_by_key(spreadsheet_id).worksheet('Machines')

# ดึงข้อมูลจาก part_code_master, Employees, และ Machines
part_codes = [part['รหัสงาน'] for part in part_code_master_sheet.get_all_records()]
employee_names = [employee['ชื่อพนักงาน'] for employee in employees_sheet.get_all_records()]
machines = [machine['machines_name'] for machine in machines_sheet.get_all_records()]

# ฟังก์ชันในการอัพเดตสถานะและเวลา
def add_status_timestamp(row_data, status_column_index, status_value):
    timestamp = datetime.now().strftime('%d-%m-%Y %H:%M')
    row_data[status_column_index] = status_value
    row_data[status_column_index + 1] = timestamp  # เพิ่ม Timestamp
    return row_data

# Forming Mode
def forming_mode():
    st.header("Forming Mode (FM)")

    department_from = 'Forming'
    department_to = st.selectbox("เลือกแผนกปลายทาง", ['Tapping', 'Final Inspection', 'Out Source'])
    woc_number = st.text_input("หมายเลข WOC")
    part_name = st.selectbox("รหัสงาน / Part Name", part_codes)
    employee_name = st.selectbox("ชื่อพนักงาน", employee_names)
    lot_number = st.text_input("หมายเลข LOT")
    total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
    barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
    sample_weight = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1)

    # คำนวณจำนวนชิ้นงาน
    if total_weight and barrel_weight and sample_weight and sample_count:
        pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)
        st.write(f"จำนวนชิ้นงาน: {pieces_count:.2f}")
    
    if st.button("บันทึก"):
        row_data = [woc_number, part_name, employee_name, department_from, department_to, lot_number, total_weight, barrel_weight, sample_weight, sample_count, pieces_count]
        row_data = add_status_timestamp(row_data, 11, "WIP-Forming")  # Add timestamp for WIP Forming
        sheet.append_row(row_data)  # บันทึกข้อมูลลง Google Sheets
        st.success("บันทึกข้อมูลสำเร็จ!")

# Tapping Mode
def tapping_mode():
    st.header("Tapping Mode (TP)")

    job_data = sheet.get_all_records()  # ดึงข้อมูลจาก Google Sheets
    st.write("ข้อมูลงานที่ถูก Transfer:")
    st.write(job_data)

    # เลือก WOC ที่รับจากแผนก Forming
    job_woc = st.selectbox("เลือกหมายเลข WOC", [job['WOC Number'] for job in job_data if job['Department From'] == 'Forming'])

    if job_woc:
        st.write(f"เลือกหมายเลข WOC: {job_woc}")
        total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
        barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
        sample_weight = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0)
        sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1)

        # คำนวณจำนวนชิ้นงาน
        if total_weight and barrel_weight and sample_weight and sample_count:
            pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)
            st.write(f"จำนวนชิ้นงาน: {pieces_count:.2f}")

        if st.button("คำนวณและเปรียบเทียบ"):
            # เปรียบเทียบระหว่าง Forming กับ Tapping
            forming_pieces_count = 1000  # ดึงจากข้อมูล Forming
            difference = abs(pieces_count - forming_pieces_count) / forming_pieces_count * 100
            st.write(f"จำนวนชิ้นงานแตกต่างกัน: {difference:.2f}%")
            
            # บันทึกข้อมูล
            row_data = [job_woc, pieces_count, difference]
            row_data = add_status_timestamp(row_data, 12, "WIP-Tapping")  # Add timestamp for WIP Tapping
            sheet.append_row(row_data)  # บันทึกลง Google Sheets
            st.success("บันทึกข้อมูลสำเร็จ!")

# Main Function to switch between modes
def main():
    st.title("ระบบการรับส่งงานระหว่างแผนก")
    mode = st.sidebar.selectbox("เลือกโหมด", ['Forming Mode', 'Tapping Mode'])

    if mode == 'Forming Mode':
        forming_mode()
    elif mode == 'Tapping Mode':
        tapping_mode()

if __name__ == "__main__":
    main()
