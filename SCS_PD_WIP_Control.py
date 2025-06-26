import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime

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
sheet = client.open_by_key(spreadsheet_id).worksheet('Jobs')  # "Jobs" sheet
part_code_master_sheet = client.open_by_key(spreadsheet_id).worksheet('part_code_master')
employees_sheet = client.open_by_key(spreadsheet_id).worksheet('Employees')

# Function to read part codes from the "part_code_master" sheet
def get_part_codes():
    try:
        part_codes = part_code_master_sheet.get_all_records()
        part_code_list = [part_code['รหัสงาน'] for part_code in part_codes]
        return part_code_list
    except Exception as e:
        st.error(f"Error reading part codes: {e}")
        return []

# Function to read employee names from the "Employees" sheet
def get_employee_names():
    try:
        employees = employees_sheet.get_all_records()
        employee_names = [employee['ชื่อพนักงาน'] for employee in employees]
        return employee_names
    except Exception as e:
        st.error(f"Error reading employee names: {e}")
        return []

# Function to add timestamp to every row update
def add_timestamp(row_data):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Get current timestamp
    row_data.append(timestamp)  # Add timestamp to the row
    return row_data

# Function to send Telegram message
def send_telegram_message(message):
    TELEGRAM_TOKEN = st.secrets["telegram"]["telegram_bot_token"]  # Retrieve Telegram token from secrets
    CHAT_ID = st.secrets["telegram"]["chat_id"]  # Retrieve chat ID from secrets

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    requests.get(url)

# Forming Mode
def forming_mode():
    st.header("Forming Mode")
    
    # Fetch part codes and employee names from Google Sheets
    part_codes = get_part_codes()  # Fetch part codes from the "part_code_master" sheet
    employee_names = get_employee_names()  # Fetch employee names from the "Employees" sheet

    # Create two columns layout
    col1, col2 = st.columns(2)
    
    with col1:
        department_from = st.selectbox('เลือกแผนกต้นทาง', ['Forming', 'Tapping', 'Final'])
        department_to = st.selectbox('เลือกแผนกปลายทาง', ['Forming', 'Tapping', 'Final'])
        woc_number = st.text_input("หมายเลข WOC")
        lot_number = st.text_input("หมายเลข LOT")
        selected_part_code = st.selectbox("รหัสงาน / Part Name", part_codes)  # Dropdown for selecting part code
    
    with col2:
        selected_employee = st.selectbox("ชื่อพนักงาน", employee_names)  # Dropdown for selecting employee name
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
        row_data = [woc_number, selected_part_code, selected_employee, department_from, department_to, lot_number, total_weight, barrel_weight, sample_weight, sample_count, pieces_count, "WIP-Forming"]
        row_data = add_timestamp(row_data)  # Add timestamp to the row
        sheet.append_row(row_data)  # Save the row to "Jobs" sheet
        st.success("บันทึกข้อมูลสำเร็จ!")
        send_telegram_message(f"Job from {department_from} to {department_to} saved!")

# Tapping Mode
def tapping_mode():
    st.header("Tapping Mode")
    job_data = sheet.get_all_records()  # Fetch all jobs from Google Sheets
    st.write("ข้อมูลงานที่ถูก Transfer:")
    st.write(job_data)

    # Select a job
    job_woc = st.selectbox("เลือกหมายเลข WOC", [job['WOC'] for job in job_data])

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
            row_data = [job_woc, pieces_count, difference, "WIP-Tapping"]
            row_data = add_timestamp(row_data)  # Add timestamp to the row
            sheet.append_row(row_data)  # Save to sheet
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
