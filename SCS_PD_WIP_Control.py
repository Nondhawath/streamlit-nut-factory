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
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_credentials, scope)
client = gspread.authorize(creds)

# Use Spreadsheet ID (Replace with your actual spreadsheet ID)
spreadsheet_id = '1GbHXO0d2GNXEwEZfeygGqNEBRQJQUoC_MO1mA-389gE'  # Replace this with your actual Spreadsheet ID

# Access the sheets using Spreadsheet ID
try:
    sheet = client.open_by_key(spreadsheet_id).worksheet('Jobs')  # "Jobs" sheet
    part_code_master_sheet = client.open_by_key(spreadsheet_id).worksheet('part_code_master')
    employees_sheet = client.open_by_key(spreadsheet_id).worksheet('Employees')
    transfer_logs_sheet = client.open_by_key(spreadsheet_id).worksheet('Transfer Logs')
except gspread.exceptions.APIError as e:
    st.error(f"API Error: {e}")
except gspread.exceptions.SpreadsheetNotFound as e:
    st.error(f"Spreadsheet not found: {e}")
except Exception as e:
    st.error(f"An error occurred: {e}")

# Function to send Telegram message
def send_telegram_message(message):
    TELEGRAM_TOKEN = st.secrets["telegram"]["telegram_bot_token"]  # Retrieve Telegram token from secrets
    CHAT_ID = st.secrets["telegram"]["chat_id"]  # Retrieve chat ID from secrets

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    requests.get(url)

# Function to read part codes from the "part_code_master" sheet
@st.cache(ttl=60)  # Cache the function result for 60 seconds to avoid too many requests
def get_part_codes():
    try:
        part_codes = part_code_master_sheet.get_all_records()
        part_code_list = [part_code['รหัสงาน'] for part_code in part_codes]
        return part_code_list
    except Exception as e:
        st.error(f"Error reading part codes: {e}")
        return []

# Function to read employee names from the "Employees" sheet
@st.cache(ttl=60)  # Cache the function result for 60 seconds to avoid too many requests
def get_employee_names():
    try:
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

# Function to find WOC row
def find_woc_row(woc_number):
    try:
        job_data = sheet.get_all_records()  # Fetch all jobs from Google Sheets
        for idx, job in enumerate(job_data):
            if job.get("WOC Number") == woc_number:  # Check if WOC Number matches
                return idx + 2  # Return the row index (gspread is 1-indexed, so we add 2)
        return None  # If WOC Number doesn't exist, return None
    except Exception as e:
        st.error(f"Error finding WOC row: {e}")
        return None

# Function to update the row in the Google Sheets
def update_woc_row(woc_number, row_data):
    row = find_woc_row(woc_number)
    if row:
        current_row_data = sheet.row_values(row)
        
        # Ensure the row_data has the same size as current_row_data
        if len(current_row_data) < 13:
            # Pad the current_row_data if there are fewer columns
            current_row_data += [''] * (13 - len(current_row_data))  # Ensure there are 13 columns

        # Update the columns (Ensure you have the correct indices here)
        current_row_data[0] = row_data[0]  # WOC Number (index 0)
        current_row_data[1] = row_data[1]  # Part Name (index 1)
        current_row_data[2] = row_data[2]  # Employee (index 2)
        current_row_data[3] = row_data[3]  # Department From (index 3)
        current_row_data[4] = row_data[4]  # Department To (index 4)
        current_row_data[5] = row_data[5]  # Lot Number (index 5)
        current_row_data[6] = row_data[6]  # Total Weight (index 6)
        current_row_data[7] = row_data[7]  # Barrel Weight (index 7)
        current_row_data[8] = row_data[8]  # Sample Weight (index 8)
        current_row_data[9] = row_data[9]  # Sample Count (index 9)
        current_row_data[10] = row_data[10]  # Pieces Count (index 10)
        current_row_data[11] = row_data[11]  # WIP Status (index 11)
        current_row_data[12] = row_data[12]  # Timestamp (index 12)

        # Update the row in the Google Sheet
        sheet.update(f"A{row}:M{row}", [current_row_data])  # Update the whole row from A to M
    else:
        # If WOC doesn't exist, append it as a new row
        sheet.append_row(row_data)  # Append new row to the sheet

# Forming Mode
def forming_mode():
    st.header("Forming Mode")
    department_from = st.selectbox('เลือกแผนกต้นทาง', ['Forming'])
    department_to = st.selectbox('เลือกแผนกปลายทาง', ['Tapping', 'Final'])
    woc_number = st.text_input("หมายเลข WOC")
    part_name = st.selectbox("รหัสงาน / Part Name", get_part_codes())  # Fetch part names dynamically
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
        row_data = [woc_number, part_name, employee, department_from, department_to, lot_number, total_weight, barrel_weight, sample_weight, sample_count, pieces_count, "WIP-Forming"]  # Add WIP status
        row_data = add_timestamp(row_data)  # Add timestamp to the row
        sheet.append_row(row_data)  # Save the row to "Jobs" sheet
        st.success("บันทึกข้อมูลสำเร็จ!")
        send_telegram_message(f"Job from {department_from} to {department_to} saved!")

# Tapping Mode
def tapping_mode():
    st.header("Tapping Mode")
    job_data = sheet.get_all_records()  # Fetch all jobs from Google Sheets

    st.write("ข้อมูลงานที่ถูก Transfer:")
    job_data_for_display = [{"WOC Number": job["WOC Number"], "Part Name": job["Part Name"], "Department From": job["Department From"], "Department To": job["Department To"], "Total Weight": job["Total Weight"], "Timestamp": job["Timestamp"]} for job in job_data]

    # Use st.table() or st.dataframe() for a cleaner display
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
            # Prepare row data for Tapping
            row_data = [job_woc, pieces_count_tapping, difference_percentage, "WIP-Tapping", datetime.now(pytz.timezone('Asia/Bangkok')).strftime('%Y-%m-%d %H:%M:%S')]
            
            # Update the WOC row or add it as a new row
            update_woc_row(job_woc, row_data)
            st.success("บันทึกข้อมูลสำเร็จ!")
            send_telegram_message(f"Job WOC {job_woc} processed in Tapping")

# Main app logic
def main():
    st.title("ระบบรับส่งงานระหว่างแผนกในโรงงาน")
    mode = st.selectbox("เลือกโหมดการทำงาน", ['Forming', 'Tapping', 'Final Inspection', 'Final Work', 'TP Transfer'])

    if mode == 'Forming':
        forming_mode()
    elif mode == 'Tapping':
        tapping_mode()
    elif mode == 'Final Inspection':
        pass
    elif mode == 'Final Work':
        pass
    elif mode == 'TP Transfer':
        pass

if __name__ == "__main__":
    main()
