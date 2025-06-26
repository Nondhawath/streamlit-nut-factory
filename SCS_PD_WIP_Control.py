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

# Error handling for Google Sheets connection
try:
    client = gspread.authorize(creds)
    # Replace with your actual Spreadsheet ID
    sheet = client.open_by_key('1GbHXO0d2GNXEwEZfeygGqNEBRQJQUoC_MO1mA-389gE').worksheet('Jobs')  
    part_code_master_sheet = client.open_by_key('1GbHXO0d2GNXEwEZfeygGqNEBRQJQUoC_MO1mA-389gE').worksheet('part_code_master')
    employees_sheet = client.open_by_key('1GbHXO0d2GNXEwEZfeygGqNEBRQJQUoC_MO1mA-389gE').worksheet('Employees')
except gspread.exceptions.GSpreadException as e:
    st.error(f"Error connecting to Google Sheets: {e}")
    raise

# Function to send Telegram message
def send_telegram_message(message):
    TELEGRAM_TOKEN = st.secrets["telegram"]["telegram_bot_token"]  # Retrieve Telegram token from secrets
    CHAT_ID = st.secrets["telegram"]["chat_id"]  # Retrieve chat ID from secrets

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    requests.get(url)

# Function to add timestamp to every status change
def add_status_timestamp(row_data, status_column_index, status_value):
    tz = pytz.timezone('Asia/Bangkok')  # Set timezone to 'Asia/Bangkok' (Thailand Time)
    timestamp = datetime.now(tz).strftime('%d-%m-%Y %H:%M')  # Get current timestamp in Thailand time

    # Update the status column and corresponding timestamp
    row_data[status_column_index] = status_value
    row_data[status_column_index + 1] = timestamp  # Add timestamp next to the status

    return row_data

# Function to check if the WOC already exists and return the row index
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
        if len(current_row_data) < 16:
            current_row_data += [''] * (16 - len(current_row_data))

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
        current_row_data[11] = row_data[11]  # WIP Forming (index 11)
        current_row_data[12] = row_data[12]  # Timestamp (index 12)
        current_row_data[13] = row_data[13]  # WIP Tapping (index 13)
        current_row_data[14] = row_data[14]  # WIP Final Inspection (index 14)
        current_row_data[15] = row_data[15]  # WIP Final Work (index 15)

        # Update the row in the Google Sheet
        sheet.update(f"A{row}:P{row}", [current_row_data])  # Update the whole row
    else:
        # If WOC doesn't exist, add it as a new row
        sheet.append_row(row_data)  # Append new row to the sheet

# Forming Mode
def forming_mode():
    st.header("Forming Mode")
    department_from = st.selectbox('เลือกแผนกต้นทาง', ['Forming', 'Tapping', 'Final'])
    department_to = st.selectbox('เลือกแผนกปลายทาง', ['Forming', 'Tapping', 'Final'])
    woc_number = st.text_input("หมายเลข WOC")
    part_name = st.selectbox("รหัสงาน / Part Name", get_part_codes())  # Fetch part names dynamically
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
        row_data = [woc_number, part_name, department_from, department_to, lot_number, total_weight, barrel_weight, sample_weight, sample_count, pieces_count]
        row_data = add_status_timestamp(row_data, 11, "WIP-Forming")  # Add timestamp to the row
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

            row_data = [job_woc, pieces_count, difference, "WIP-Tapping"]
            row_data = add_status_timestamp(row_data, 13, "WIP-Tapping")  # Add timestamp to the row

            update_woc_row(job_woc, row_data)
            st.success("บันทึกข้อมูลสำเร็จ!")
            send_telegram_message(f"Job WOC {job_woc} processed in Tapping")

# Tapping Work Mode
def tapping_work_mode():
    st.header("Tapping Work Mode")
    job_data = sheet.get_all_records()  # Fetch all jobs from Google Sheets

    st.write("งานที่มีสถานะ WIP-Tapping:")
    job_data_for_display = [{"WOC Number": job["WOC Number"], "Part Name": job["Part Name"], "Employee": job["Employee"], "Department From": job["Department From"], "Department To": job["Department To"], "Timestamp": job["Timestamp"]} for job in job_data]

    st.dataframe(job_data_for_display)  # Show a table of job data without unnecessary JSON fields

    # Select a job
    job_woc = st.selectbox("เลือกหมายเลข WOC", [job['WOC Number'] for job in job_data])

    # Choose machine
    machine_name = st.selectbox("เลือกเครื่องจักร", ["TP30", "SM30", "Other"])

    if st.button("บันทึก"):
        row_data = [job_woc, machine_name]
        row_data = add_status_timestamp(row_data, 13, f"Used - {machine_name}")  # Update status and add timestamp

        update_woc_row(job_woc, row_data)
        st.success(f"งาน WOC {job_woc} ถูกบันทึกเป็น Used - {machine_name}")
        send_telegram_message(f"Job WOC {job_woc} processed on {machine_name}")

# Main app logic
def main():
    st.title("ระบบรับส่งงานระหว่างแผนกในโรงงาน")
    mode = st.radio("เลือกโหมด", ['Forming', 'Tapping', 'Tapping Work', 'Final Inspection', 'Final Work', 'TP Transfer'])

    if mode == 'Forming':
        forming_mode()
    elif mode == 'Tapping':
        tapping_mode()
    elif mode == 'Tapping Work':
        tapping_work_mode()

if __name__ == "__main__":
    main()
