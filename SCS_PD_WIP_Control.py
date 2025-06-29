import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime
import pytz

# Setting up Google Sheets Connection
google_credentials = st.secrets["google_service_account"]  # Get Google credentials directly from secrets

# Define the scope for Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Authorize the credentials and set up the client
@st.cache_resource  # Cache the Google Sheets client for reuse
def get_google_sheets_client():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(google_credentials, scope)
    client = gspread.authorize(creds)
    return client

# Use Spreadsheet ID (Replace with your actual spreadsheet ID)
spreadsheet_id = '1GbHXO0d2GNXEwEZfeygGqNEBRQJQUoC_MO1mA-389gE'  # Replace this with your actual Spreadsheet ID

# Access the sheets using Spreadsheet ID
def open_sheets():
    try:
        client = get_google_sheets_client()  # Use the cached Google Sheets client
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

# Function to send Telegram message
def send_telegram_message(message):
    TELEGRAM_TOKEN = st.secrets["telegram"]["telegram_bot_token"]  # Retrieve Telegram token from secrets
    CHAT_ID = st.secrets["telegram"]["chat_id"]  # Retrieve chat ID from secrets

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    requests.get(url)

# Function to read part codes from the "part_code_master" sheet with caching
@st.cache_data(ttl=60)  # Cache data for 60 seconds to avoid exceeding API quota
def get_part_codes():
    try:
        # Fetch all records from the part_code_master sheet
        part_code_master_sheet = open_sheets()[1]
        part_codes = part_code_master_sheet.get_all_records()
        part_code_list = [part_code['รหัสงาน'] for part_code in part_codes]
        return part_code_list
    except Exception as e:
        st.error(f"Error reading part codes: {e}")
        return []

# Function to read employee names from the "Employees" sheet with caching
@st.cache_data(ttl=60)  # Cache data for 60 seconds to avoid exceeding API quota
def get_employee_names():
    try:
        employees_sheet = open_sheets()[2]
        employees = employees_sheet.get_all_records()
        employee_names = [employee['ชื่อพนักงาน'] for employee in employees]
        return employee_names
    except Exception as e:
        st.error(f"Error reading employee names: {e}")
        return []

# Function to add timestamp to every row update (with timezone)
def add_timestamp(row_data):
    tz = pytz.timezone('Asia/Bangkok')  # Set timezone to 'Asia/Bangkok' (Thailand Time)
    timestamp = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')  # Get current timestamp in Thailand time
    row_data.append(timestamp)  # Add timestamp to the row
    return row_data

# Function to log transfer data into "Transfer Logs" sheet
def log_transfer_to_logs(woc_number, part_name, employee, department_from, department_to, lot_number, total_weight, barrel_weight, sample_weight, sample_count, pieces_count):
    try:
        transfer_logs_sheet = open_sheets()[3]  # Get Transfer Logs sheet (this returns the correct sheet)
        timestamp = datetime.now(pytz.timezone('Asia/Bangkok')).strftime('%Y-%m-%d %H:%M:%S')
        
        # Prepare row data for logging transfer
        row_data = [woc_number, part_name, employee, department_from, department_to, lot_number, total_weight, barrel_weight, sample_weight, sample_count, pieces_count, timestamp, "Transferred", "None"]
        transfer_logs_sheet.append_row(row_data)  # Append the data to Transfer Logs sheet
        
        st.success("Transfer logged successfully!")
        send_telegram_message(f"WOC {woc_number} transferred from {department_from} to {department_to}")
        
    except Exception as e:
        st.error(f"Error logging transfer: {e}")

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
        # Check if WOC Number already exists to avoid duplicates
        existing_row = sheet.find(woc_number)
        if existing_row:
            st.error(f"WOC Number {woc_number} already exists. Please use a different number.")
        else:
            # Save data to Google Sheets with timestamp
            row_data = [woc_number, part_name, employee, department_from, department_to, lot_number, total_weight, barrel_weight, sample_weight, sample_count, pieces_count, "WIP-Forming"]
            row_data = add_timestamp(row_data)  # Add timestamp to the row
            sheet.append_row(row_data)  # Save the row to "Jobs" sheet
            st.success("บันทึกข้อมูลสำเร็จ!")
        
            # Log the transfer in the Transfer Logs sheet
            log_transfer_to_logs(woc_number, part_name, employee, department_from, department_to, lot_number, total_weight, barrel_weight, sample_weight, sample_count, pieces_count)

# Tapping Mode
def tapping_mode(sheet):
    st.header("Tapping Mode")
    
    @st.cache_data(ttl=60)  # Cache the job data for 60 seconds to avoid exceeding API quota
    def fetch_job_data():
        try:
            # Define the expected headers explicitly
            expected_headers = ['WOC Number', 'Part Name', 'Employee', 'Department From', 'Department To', 
                                'Lot Number', 'Total Weight', 'Barrel Weight', 'Sample Weight', 'Sample Count', 
                                'Pieces Count', 'WIP Status', 'Timestamp', 'WOC Source']  # Modify based on your actual header row
            
            # Fetch the records with the expected headers
            job_data = sheet.get_all_records(expected_headers=expected_headers)
            return job_data
        except gspread.exceptions.GSpreadException as e:
            st.error(f"Error reading job data: {e}")
            return []

    job_data = fetch_job_data()  # Fetch job data from cache
    
    st.write("ข้อมูลงานที่ถูก Transfer:")
    job_data_for_display = [{"WOC Number": job["WOC Number"], "Part Name": job["Part Name"], "Department From": job["Department From"], "Department To": job["Department To"], "Total Weight": job["Total Weight"], "Timestamp": job["Timestamp"]} for job in job_data]

    st.dataframe(job_data_for_display)  # Show a table of job data without unnecessary JSON fields

    # Select a job
    job_woc = st.selectbox("เลือกหมายเลข WOC", [job['WOC Number'] for job in job_data])

    if job_woc:
        st.write(f"เลือกหมายเลข WOC: {job_woc}")
        
        # Get the Pieces Count from Forming for comparison
        forming_job = next((job for job in job_data if job['WOC Number'] == job_woc), None)
        if forming_job:
            pieces_count_forming = forming_job.get('Pieces Count', 0)
        else:
            pieces_count_forming = 0  # Default value if no Forming data found

        # Form for checking weight and calculation
        total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
        barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
        sample_weight = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0)
        sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1)

        if total_weight and barrel_weight and sample_weight and sample_count:
            pieces_count_tapping = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)
            st.write(f"จำนวนชิ้นงานใน Tapping: {pieces_count_tapping:.2f}")

            # Calculate the percentage difference
            if pieces_count_forming > 0:
                difference_percentage = abs(pieces_count_tapping - pieces_count_forming) / pieces_count_forming * 100
                st.write(f"จำนวนชิ้นงานแตกต่างกัน: {difference_percentage:.2f}%")
            else:
                st.warning("ไม่พบข้อมูลจำนวนชิ้นงานจาก Forming เพื่อทำการเปรียบเทียบ")

        if st.button("คำนวณและเปรียบเทียบ"):
            # Prepare row data for Tapping with WOC Source linking to Forming
            row_data = [job_woc, pieces_count_tapping, difference_percentage, "WIP-Tapping", job_woc, datetime.now(pytz.timezone('Asia/Bangkok')).strftime('%Y-%m-%d %H:%M:%S')]
            
            # Instead of updating, append as a new row in the Google Sheets
            sheet.append_row(row_data)
            st.success("บันทึกข้อมูลสำเร็จ!")
            send_telegram_message(f"Job WOC {job_woc} processed in Tapping")

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
