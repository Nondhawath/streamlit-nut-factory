import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Set up Google Sheets Connection
google_credentials = st.secrets["google_service_account"]  # Get Google credentials from secrets

# Define the scope for Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Authorize the credentials and set up the client
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_credentials, scope)
client = gspread.authorize(creds)

# Use Spreadsheet ID (Replace with your actual spreadsheet ID)
spreadsheet_id = '1GbHXO0d2GNXEwEZfeygGqNEBRQJQUoC_MO1mA-389gE'  # Replace this with your actual Spreadsheet ID

# Accessing the sheets using Spreadsheet ID
sheet = client.open_by_key(spreadsheet_id).worksheet('Jobs')  # "Jobs" sheet
part_code_master_sheet = client.open_by_key(spreadsheet_id).worksheet('part_code_master')  # "part_code_master" sheet
employees_sheet = client.open_by_key(spreadsheet_id).worksheet('Employees')  # "Employees" sheet
machines_sheet = client.open_by_key(spreadsheet_id).worksheet('Machines')  # "Machines" sheet

# Function to add status and timestamp to row
def add_status_timestamp(row_data, status_column_index, status_value):
    # Check if the row_data has enough columns, add empty values if not
    while len(row_data) <= status_column_index:
        row_data.append('')  # Add empty cell if not enough columns

    # Add the status value to the row at the specified index
    row_data[status_column_index] = status_value

    # Add timestamp next to the status
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    row_data.append(timestamp)

    return row_data

# Function to update WOC status with timestamp
def update_woc_status(woc_number, status, part_name):
    row_data = [woc_number, status, part_name]
    row_data = add_status_timestamp(row_data, 2, status)  # Adding timestamp and status
    sheet.append_row(row_data)  # Save to "Jobs" sheet

# Forming Mode - Sending work to another department
def forming_mode():
    st.header("Forming Mode (FM)")

    # Dropdown for selecting Part Name
    part_code_master_data = part_code_master_sheet.get_all_records()  # Fetch all part codes from the sheet
    part_name = st.selectbox("รหัสงาน / Part Name", [part['Part Name'] for part in part_code_master_data])

    # Select employee from Employees Sheet
    employees_data = employees_sheet.get_all_records()
    employee_name = st.selectbox("ชื่อพนักงาน", [employee['Employee Name'] for employee in employees_data])

    # Input fields for transferring data
    department_from = 'FM'  # Forming is always the sending department
    department_to = st.selectbox("แผนกปลายทาง", ['TP', 'FI', 'OS'])  # Can select the receiving department
    lot_number = st.text_input("หมายเลข LOT")
    total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
    barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
    sample_weight = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1)

    # Calculate pieces count
    if total_weight and barrel_weight and sample_weight and sample_count:
        pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)
        st.write(f"จำนวนชิ้นงาน: {pieces_count:.2f}")

    # Button to save data
    if st.button("บันทึก"):
        row_data = [f"WOC-{datetime.now().strftime('%Y%m%d%H%M%S')}", part_name, employee_name, department_from, department_to, lot_number, total_weight, barrel_weight, sample_weight, sample_count, pieces_count]
        row_data = add_status_timestamp(row_data, 10, "WIP-Forming")  # Add status for WIP Forming and timestamp
        sheet.append_row(row_data)  # Save the row to "Jobs" sheet
        st.success("บันทึกข้อมูลสำเร็จ!")

# Tapping Mode - Receiving work and transferring
def tapping_mode():
    st.header("Tapping Mode (TP)")

    # Fetch jobs from the sheet
    job_data = sheet.get_all_records()  # Fetch all jobs from Google Sheets
    woc_numbers = [job['WOC Number'] for job in job_data]
    job_woc = st.selectbox("เลือกหมายเลข WOC", woc_numbers)

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
            # Compare with forming mode pieces count
            forming_pieces_count = 1000  # Fetch this value from Forming mode data
            difference = abs(pieces_count - forming_pieces_count) / forming_pieces_count * 100
            st.write(f"จำนวนชิ้นงานแตกต่างกัน: {difference:.2f}%")
            row_data = [job_woc, pieces_count, difference]
            row_data = add_status_timestamp(row_data, 10, "WIP-Tapping")  # Add status for WIP Tapping and timestamp
            sheet.append_row(row_data)  # Save to sheet
            st.success("บันทึกข้อมูลสำเร็จ!")

# Main function to handle the modes
def main():
    st.title("ระบบรับส่งงานระหว่างแผนกในโรงงาน")

    mode = st.radio("เลือกโหมด", ['Forming', 'Tapping'])

    if mode == 'Forming':
        forming_mode()
    elif mode == 'Tapping':
        tapping_mode()

if __name__ == "__main__":
    main()
