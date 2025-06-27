import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Google Sheets setup
google_credentials = st.secrets["google_service_account"]  # Get Google credentials directly from secrets

# Define the scope for Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Authorize the credentials and set up the client
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_credentials, scope)
client = gspread.authorize(creds)

# Spreadsheet ID (Replace with your actual Spreadsheet ID)
spreadsheet_id = '1GbHXO0d2GNXEwEZfeygGqNEBRQJQUoC_MO1mA-389gE'  # Replace this with your actual Spreadsheet ID

# Function to cache data from Google Sheets
@st.cache_data
def get_sheet_data(sheet_name):
    sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
    return sheet.get_all_records()

# Use the cached data
part_code_master_data = get_sheet_data('part_code_master')
employee_data = get_sheet_data('Employees')
machine_data = get_sheet_data('Machines')
job_data = get_sheet_data('Jobs')

# Function to add timestamp to every row update
def add_status_timestamp(row_data, status_column_index, status_value):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Get current timestamp
    row_data[status_column_index] = status_value  # Add status to the row
    row_data[status_column_index + 1] = timestamp  # Add timestamp next to the status
    return row_data

# Forming Mode
def forming_mode():
    st.header("Forming Mode")
    department_from = st.selectbox('เลือกแผนกต้นทาง', ['Forming'])
    department_to = st.selectbox('เลือกแผนกปลายทาง', ['Tapping', 'Final Inspection', 'Outsource'])
    woc_number = st.text_input("หมายเลข WOC")
    
    # ตรวจสอบข้อมูลที่ดึงมาจาก Google Sheets
    st.write("Part Code Master Data:", part_code_master_data)

    # ตรวจสอบว่า column 'รหัสงาน' มีอยู่จริง
    part_names = [part['รหัสงาน'] for part in part_code_master_data if 'รหัสงาน' in part]
    st.write("Part Names:", part_names)

    part_name = st.selectbox("รหัสงาน / Part Name", part_names)
    lot_number = st.text_input("หมายเลข LOT")
    total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
    barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
    sample_weight = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1)

    # Calculate number of pieces
    if total_weight and barrel_weight and sample_weight and sample_count:
        pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)
        st.write(f"จำนวนชิ้นงาน: {pieces_count:.2f}")
    
    if st.button("บันทึก"):
        employee = st.selectbox("ชื่อพนักงาน", [employee['ชื่อพนักงาน'] for employee in employee_data])
        row_data = [woc_number, part_name, employee, department_from, department_to, lot_number, total_weight, barrel_weight, sample_weight, sample_count, pieces_count]
        row_data = add_status_timestamp(row_data, 11, "WIP-Forming")  # Add timestamp for WIP-Forming status
        job_sheet = client.open_by_key(spreadsheet_id).worksheet('Jobs')
        job_sheet.append_row(row_data)  # Save the row to "Jobs" sheet
        st.success("บันทึกข้อมูลสำเร็จ!")

# Tapping Mode
def tapping_mode():
    st.header("Tapping Mode")
    job_data = job_data  # Fetch all jobs from Google Sheets
    st.write("ข้อมูลงานที่ถูก Transfer:")
    st.write(job_data)

    # Select a job
    job_woc = st.selectbox("เลือกหมายเลข WOC", [job['WOC Number'] for job in job_data])

    if job_woc:
        st.write(f"เลือกหมายเลข WOC: {job_woc}")
        # Form for checking weight
        total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
        barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
        sample_weight = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0)
        sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1)

        if total_weight and barrel_weight and sample_weight and sample_count:
            pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)
            st.write(f"จำนวนชิ้นงาน: {pieces_count:.2f}")

        if st.button("คำนวณและเปรียบเทียบ"):
            # Compare with forming mode pieces count
            forming_pieces_count = 1000  # Fetch this value from Forming mode data
            difference = abs(pieces_count - forming_pieces_count) / forming_pieces_count * 100
            st.write(f"จำนวนชิ้นงานแตกต่างกัน: {difference:.2f}%")
            
            # Save data to Google Sheets with timestamp
            row_data = [job_woc, pieces_count, difference]
            row_data = add_status_timestamp(row_data, 12, "WIP-Tapping")  # Add timestamp for WIP-Tapping status
            job_sheet = client.open_by_key(spreadsheet_id).worksheet('Jobs')
            job_sheet.append_row(row_data)  # Save the row to "Jobs" sheet
            st.success("บันทึกข้อมูลสำเร็จ!")

# Final Inspection Mode
def final_inspection_mode():
    st.header("Final Inspection Mode")
    job_data = job_data  # Fetch all jobs from Google Sheets
    st.write("ข้อมูลงานที่ถูก Transfer:")
    st.write(job_data)

    # Select a job
    job_woc = st.selectbox("เลือกหมายเลข WOC", [job['WOC Number'] for job in job_data])

    if job_woc:
        st.write(f"เลือกหมายเลข WOC: {job_woc}")
        # Form for checking weight
        total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
        barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
        sample_weight = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0)
        sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1)

        if total_weight and barrel_weight and sample_weight and sample_count:
            pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)
            st.write(f"จำนวนชิ้นงาน: {pieces_count:.2f}")

        if st.button("คำนวณและเปรียบเทียบ"):
            # Compare with tapping mode pieces count
            tapping_pieces_count = 1200  # Fetch this value from Tapping mode data
            difference = abs(pieces_count - tapping_pieces_count) / tapping_pieces_count * 100
            st.write(f"จำนวนชิ้นงานแตกต่างกัน: {difference:.2f}%")
            
            # Save data to Google Sheets with timestamp
            row_data = [job_woc, pieces_count, difference]
            row_data = add_status_timestamp(row_data, 13, "WIP-Final Inspection")  # Add timestamp for WIP-Final Inspection status
            job_sheet = client.open_by_key(spreadsheet_id).worksheet('Jobs')
            job_sheet.append_row(row_data)  # Save the row to "Jobs" sheet
            st.success("บันทึกข้อมูลสำเร็จ!")

# Main app logic
def main():
    st.title("ระบบรับส่งงานระหว่างแผนกในโรงงาน")
    mode = st.sidebar.selectbox("เลือกโหมด", ['Forming', 'Tapping', 'Final Inspection'])

    if mode == 'Forming':
        forming_mode()
    elif mode == 'Tapping':
        tapping_mode()
    elif mode == 'Final Inspection':
        final_inspection_mode()

if __name__ == "__main__":
    main()
