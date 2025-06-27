import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time

# ฟังก์ชันเชื่อมต่อกับ Google Sheets
def connect_to_google_sheets():
    try:
        google_credentials = st.secrets["google_service_account"]  # Get Google credentials from secrets

        # Define the scope for Google Sheets API
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

        # Authorize the credentials and set up the client
        creds = ServiceAccountCredentials.from_json_keyfile_dict(google_credentials, scope)
        client = gspread.authorize(creds)

        # Use Spreadsheet ID
        spreadsheet_id = st.secrets["spreadsheet_id"]  # Spreadsheet ID from secrets
        sheet = client.open_by_key(spreadsheet_id).worksheet('Jobs')  # "Jobs" sheet
        part_code_master_sheet = client.open_by_key(spreadsheet_id).worksheet('part_code_master')  # Part code sheet

        return sheet, part_code_master_sheet
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return None, None

# ฟังก์ชันดึงข้อมูลจาก Google Sheets
def get_part_codes(part_code_master_sheet):
    try:
        part_codes = part_code_master_sheet.get_all_records()
        return [part['Part Name'] for part in part_codes]
    except Exception as e:
        st.error(f"Error fetching part codes: {e}")
        return []

# ฟังก์ชันที่เพิ่มข้อมูลการบันทึกสถานะและเวลา
def add_status_timestamp(row_data, status_column_index, status_value):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    row_data[status_column_index] = status_value
    row_data[status_column_index + 1] = timestamp
    return row_data

# ฟังก์ชันการบันทึกข้อมูลลงใน Google Sheets
def save_to_google_sheets(sheet, row_data):
    try:
        sheet.append_row(row_data)
        st.success("ข้อมูลถูกบันทึกเรียบร้อยแล้ว")
    except Exception as e:
        st.error(f"Error saving data to Google Sheets: {e}")

# โหมดการทำงานสำหรับ Forming
def forming_mode(sheet, part_code_master_sheet):
    st.header("Forming Mode (FM)")
    part_codes = get_part_codes(part_code_master_sheet)

    department_from = "FM"
    department_to = st.selectbox('เลือกแผนกปลายทาง', ['TP', 'FI', 'OS'])
    woc_number = st.text_input("หมายเลข WOC")
    part_name = st.selectbox("รหัสงาน / Part Name", part_codes)
    lot_number = st.text_input("หมายเลข LOT")
    total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
    barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
    sample_weight = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1)

    if total_weight and barrel_weight and sample_weight and sample_count:
        pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)
        st.write(f"จำนวนชิ้นงาน: {pieces_count:.2f}")

    if st.button("บันทึก"):
        row_data = [woc_number, part_name, "นายคมสันต์ คงคำลี", department_from, department_to, lot_number, total_weight, barrel_weight, sample_weight, sample_count, pieces_count]
        row_data = add_status_timestamp(row_data, 11, "WIP-Forming")
        save_to_google_sheets(sheet, row_data)

# โหมดการทำงานสำหรับ Tapping
def tapping_mode(sheet):
    st.header("Tapping Mode (TP)")
    job_data = sheet.get_all_records()

    st.write("ข้อมูลงานที่ถูก Transfer:")
    st.write(job_data)

    # เลือกหมายเลข WOC ที่ต้องการ
    job_woc = st.selectbox("เลือกหมายเลข WOC", [job['WOC Number'] for job in job_data])

    if job_woc:
        st.write(f"เลือกหมายเลข WOC: {job_woc}")
        total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
        barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
        sample_weight = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0)
        sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1)

        if total_weight and barrel_weight and sample_weight and sample_count:
            pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)
            st.write(f"จำนวนชิ้นงาน: {pieces_count:.2f}")

        if st.button("คำนวณและเปรียบเทียบ"):
            row_data = [job_woc, pieces_count]
            row_data = add_status_timestamp(row_data, 11, "WIP-Tapping")
            save_to_google_sheets(sheet, row_data)

# โหมดการทำงานสำหรับ Final Inspection
def final_inspection_mode(sheet):
    st.header("Final Inspection Mode (FI)")
    job_data = sheet.get_all_records()

    st.write("ข้อมูลงานที่ถูก Transfer:")
    st.write(job_data)

    job_woc = st.selectbox("เลือกหมายเลข WOC", [job['WOC Number'] for job in job_data])

    if job_woc:
        st.write(f"เลือกหมายเลข WOC: {job_woc}")
        total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
        barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
        sample_weight = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0)
        sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1)

        if total_weight and barrel_weight and sample_weight and sample_count:
            pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)
            st.write(f"จำนวนชิ้นงาน: {pieces_count:.2f}")

        if st.button("คำนวณและเปรียบเทียบ"):
            row_data = [job_woc, pieces_count]
            row_data = add_status_timestamp(row_data, 11, "WIP-Final Inspection")
            save_to_google_sheets(sheet, row_data)

# ฟังก์ชันหลัก
def main():
    sheet, part_code_master_sheet = connect_to_google_sheets()
    if not sheet or not part_code_master_sheet:
        return

    mode = st.sidebar.selectbox("เลือกโหมด", ["Forming Mode", "Tapping Mode", "Final Inspection Mode"])

    if mode == "Forming Mode":
        forming_mode(sheet, part_code_master_sheet)
    elif mode == "Tapping Mode":
        tapping_mode(sheet)
    elif mode == "Final Inspection Mode":
        final_inspection_mode(sheet)

if __name__ == "__main__":
    main()
