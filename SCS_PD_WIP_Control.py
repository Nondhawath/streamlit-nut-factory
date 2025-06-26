import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime
import json

# Load the Google Service Account credentials from Streamlit secrets
google_credentials = json.loads(st.secrets["google_service_account"])

# Setting up Google Sheets Connection
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_credentials, scope)
client = gspread.authorize(creds)
sheet = client.open("Factory_Job_Status").sheet1  # "Jobs" sheet
woc_status_sheet = client.open("Factory_Job_Status").worksheet('WOC_Status')  # "WOC_Status" sheet

# Telegram Bot Setup
TELEGRAM_TOKEN = st.secrets["telegram_bot_token"]  # Retrieve Telegram token from secrets
CHAT_ID = st.secrets["chat_id"]  # Retrieve chat ID from secrets

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    requests.get(url)

# Function to add timestamp to every row update
def add_timestamp(row_data):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Get current timestamp
    row_data.append(timestamp)  # Add timestamp to the row
    return row_data

# Forming Mode
def forming_mode():
    st.header("Forming Mode")
    department_from = st.selectbox('เลือกแผนกต้นทาง', ['Forming', 'Tapping', 'Final'])
    department_to = st.selectbox('เลือกแผนกปลายทาง', ['Forming', 'Tapping', 'Final'])
    woc_number = st.text_input("หมายเลข WOC")
    part_name = st.selectbox("รหัสงาน / Part Name", ["Part 1", "Part 2", "Part 3"])
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
        row_data = [department_from, department_to, woc_number, part_name, lot_number, total_weight, barrel_weight, sample_weight, sample_count, pieces_count]
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
            row_data = [job_woc, pieces_count, difference]
            row_data = add_timestamp(row_data)  # Add timestamp to the row
            sheet.append_row(row_data)  # Save to sheet
            st.success("บันทึกข้อมูลสำเร็จ!")
            send_telegram_message(f"Job WOC {job_woc} processed in Tapping")

# Function to update WOC status with timestamp
def update_woc_status(woc_number, status, part_name):
    row_data = [woc_number, status, part_name]
    row_data = add_timestamp(row_data)  # Add timestamp to the row
    woc_status_sheet.append_row(row_data)  # Save to "WOC_Status" sheet

# Main app logic
def main():
    st.title("ระบบรับส่งงานระหว่างแผนกในโรงงาน")
    mode = st.radio("เลือกโหมด", ['Forming', 'Tapping', 'Final Inspection', 'Final Work', 'TP Transfer'])

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
