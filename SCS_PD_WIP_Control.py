import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime
import pytz
import time

# Setting up Google Sheets Connection
google_credentials = st.secrets["google_service_account"]  # Get Google credentials directly from secrets

# Define the scope for Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Authorize the credentials and set up the client
@st.cache_resource  # Cache the Google Sheets client for reuse
def get_google_sheets_client():
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(google_credentials, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Error while accessing Google Sheets: {e}")
        return None

# Use Spreadsheet ID (Replace with your actual spreadsheet ID)
spreadsheet_id = '1GbHXO0d2GNXEwEZfeygGqNEBRQJQUoC_MO1mA-389gE'  # Replace this with your actual Spreadsheet ID

# Access the sheets using Spreadsheet ID
def open_sheets():
    try:
        client = get_google_sheets_client()  # Use the cached Google Sheets client
        if client is None:
            return None, None, None, None
        sheet = client.open_by_key(spreadsheet_id).worksheet('Jobs')  # "Jobs" sheet
        part_code_master_sheet = client.open_by_key(spreadsheet_id).worksheet('part_code_master')
        employees_sheet = client.open_by_key(spreadsheet_id).worksheet('Employees')
        transfer_logs_sheet = client.open_by_key(spreadsheet_id).worksheet('Transfer Logs')
        return sheet, part_code_master_sheet, employees_sheet, transfer_logs_sheet
    except gspread.exceptions.APIError as e:
        st.error(f"API Error while accessing Google Sheets: {e}")
        return None, None, None, None
    except gspread.exceptions.SpreadsheetNotFound as e:
        st.error(f"Spreadsheet not found: {e}")
        return None, None, None, None
    except gspread.exceptions.GSpreadException as e:
        st.error(f"GSpreadException: {e}")
        return None, None, None, None
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return None, None, None, None

# Function to fetch part codes from the 'part_code_master' sheet
def get_part_codes():
    try:
        part_codes = part_code_master_sheet.get_all_records()
        part_code_list = [part_code['รหัสงาน'] for part_code in part_codes]
        return part_code_list
    except Exception as e:
        st.error(f"Error reading part codes: {e}")
        return []

# Function to fetch employee names from the 'Employees' sheet
def get_employee_names():
    try:
        employees = employees_sheet.get_all_records()
        employee_names = [employee['ชื่อพนักงาน'] for employee in employees]
        return employee_names
    except Exception as e:
        st.error(f"Error reading employee names: {e}")
        return []

# Function to send Telegram message
def send_telegram_message(message):
    try:
        TELEGRAM_TOKEN = st.secrets["telegram"]["telegram_bot_token"]  # Retrieve Telegram token from secrets
        CHAT_ID = st.secrets["telegram"]["chat_id"]  # Retrieve chat ID from secrets
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
        requests.get(url)
    except Exception as e:
        st.error(f"Error sending message to Telegram: {e}")

# Function to add timestamp to every row update (with timezone)
def add_timestamp(row_data):
    tz = pytz.timezone('Asia/Bangkok')  # Set timezone to 'Asia/Bangkok' (Thailand Time)
    timestamp = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')  # Get current timestamp in Thailand time
    row_data.append(timestamp)  # Add timestamp to the row
    return row_data

# Forming Mode
def forming_mode(sheet):
    st.header("Forming Mode")
    department_from = st.selectbox('เลือกแผนกต้นทาง', ['Forming'])
    department_to = st.selectbox('เลือกแผนกปลายทาง', ['Tapping', 'Final'])
    woc_number = st.text_input("หมายเลข WOC")
    
    # Fetch part names dynamically from Google Sheets
    part_name = st.selectbox("รหัสงาน / Part Name", get_part_codes())  
    employee = st.selectbox("ชื่อพนักงาน", get_employee_names())  # Fetch employee names dynamically
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
        # Save data to Google Sheets with timestamp
        row_data = [woc_number, part_name, employee, department_from, department_to, lot_number, total_weight, barrel_weight, sample_weight, sample_count, pieces_count, "WIP-Forming"]
        row_data = add_timestamp(row_data)  # Add timestamp to the row
        sheet.append_row(row_data)  # Save the row to "Jobs" sheet
        st.success("บันทึกข้อมูลสำเร็จ!")

# Tapping Mode
def tapping_mode(sheet):
    st.header("Tapping Mode")
    
    # Fetch job data from Google Sheets with retry logic
    job_data = fetch_job_data(sheet)  # Fetch job data with retry logic
    if not job_data:
        st.error("ไม่สามารถดึงข้อมูลจาก Google Sheets ได้")
        return

    st.write("ข้อมูลงานที่ถูก Transfer:")
    job_data_for_display = [{"WOC Number": job["WOC Number"], "Part Name": job["Part Name"], "Department From": job["Department From"], "Department To": job["Department To"], "Total Weight": job["Total Weight"], "Timestamp": job["Timestamp"]} for job in job_data]

    st.dataframe(job_data_for_display)  # Show a table of job data without unnecessary JSON fields

    # Select a job
    job_woc = st.selectbox("เลือกหมายเลข WOC", [job['WOC Number'] for job in job_data])

    if job_woc:
        st.write(f"เลือกหมายเลข WOC: {job_woc}")
        
        # Form for checking weight and calculation
        total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
        barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
        sample_weight = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0)
        sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1)

        if total_weight and barrel_weight and sample_weight and sample_count:
            pieces_count_tapping = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)
            st.write(f"จำนวนชิ้นงานใน Tapping: {pieces_count_tapping:.2f}")

        if st.button("บันทึก"):
            # Update the WOC data in the Google Sheets
            update_job_data(sheet, job_woc, pieces_count_tapping, total_weight, barrel_weight, sample_weight, sample_count)

# Fetch job data with retry logic
def fetch_job_data(sheet, retries=3, delay=60):
    try:
        job_data = sheet.get_all_records()  # Fetch all jobs from Google Sheets
        return job_data
    except gspread.exceptions.APIError as e:
        st.error(f"APIError while fetching data: {e}")
        if retries > 0:
            st.warning(f"Retrying after {delay} seconds...")
            time.sleep(delay)  # Sleep for the specified delay
            return fetch_job_data(sheet, retries-1, delay)  # Retry fetching data
        else:
            st.error("Maximum retries reached. Could not fetch job data.")
            return []

# Update job data in Google Sheets (Update columns M onwards)
def update_job_data(sheet, job_woc, pieces_count_tapping, total_weight, barrel_weight, sample_weight, sample_count):
    try:
        row = sheet.find(job_woc)  # Find row based on WOC Number
        if row:
            row_data = [job_woc, pieces_count_tapping, total_weight, barrel_weight, sample_weight, sample_count, "WIP-TP"]
            row_data = add_timestamp(row_data)  # Add timestamp to the row
            sheet.update(f'M{row.row}', row_data)  # Update columns M onwards
            st.success(f"ข้อมูล WOC {job_woc} ได้รับการอัปเดตเรียบร้อยแล้ว!")
        else:
            st.error(f"ไม่พบหมายเลข WOC {job_woc}")
    except Exception as e:
        st.error(f"Error updating job data: {e}")

# Main app logic
def main():
    st.title("ระบบรับส่งงานระหว่างแผนกในโรงงาน")
    mode = st.selectbox("เลือกโหมดการทำงาน", ['Forming', 'Tapping', 'Final Inspection', 'Final Work', 'TP Transfer'])

    sheet, part_code_master_sheet, employees_sheet, transfer_logs_sheet = open_sheets()  # Open sheets

    if sheet:  # Check if the sheets were successfully opened
        if mode == 'Forming':
            forming_mode(sheet)
        elif mode == 'Tapping':
            tapping_mode(sheet)
        elif mode == 'Final Inspection':
            pass
        elif mode == 'Final Work':
            pass
        elif mode == 'TP Transfer':
            pass
    else:
        st.error("ไม่สามารถเชื่อมต่อกับ Google Sheets ได้!")

if __name__ == "__main__":
    main()
