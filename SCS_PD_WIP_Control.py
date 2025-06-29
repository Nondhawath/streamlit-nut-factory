import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Setting up Google Sheets Connection
google_credentials = st.secrets["google_service_account"]  # Get Google credentials directly from secrets

# Define the scope for Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Authorize the credentials and set up the client
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_credentials, scope)
client = gspread.authorize(creds)

# Spreadsheet ID and Sheet names
spreadsheet_id = '1GbHXO0d2GNXEwEZfeygGqNEBRQJQUoC_MO1mA-389gE'  # Replace with your actual Spreadsheet ID
sheet = client.open_by_key(spreadsheet_id).worksheet('Forming')  # "Forming" sheet
woc_status_sheet = client.open_by_key(spreadsheet_id).worksheet('WOC_Status')  # "WOC_Status" sheet

# Function to add timestamp to every row update
def add_timestamp(row_data, status_column_index, status_value):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Get current timestamp
    row_data[status_column_index] = status_value  # Update the status column
    row_data[status_column_index + 1] = timestamp  # Add timestamp next to the status
    return row_data

# Forming Mode
def forming_mode():
    st.header("Forming Mode (FM)")
    department_from = st.selectbox('เลือกแผนกต้นทาง', ['Forming'])
    department_to = st.selectbox('เลือกแผนกปลายทาง', ['Tapping', 'Final Inspection', 'Out Source'])
    woc_number = st.text_input("หมายเลข WOC")
    part_name = st.selectbox("รหัสงาน / Part Name", ["Part 1", "Part 2", "Part 3"])  # Add your parts here
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
        row_data = add_timestamp(row_data, 11, "WIP-Forming")  # Add timestamp for WIP Forming
        sheet.append_row(row_data)  # Save the row to "Forming" sheet
        st.success("บันทึกข้อมูลสำเร็จ!")

# Tapping Mode
def tapping_mode():
    st.header("Tapping Mode (TP)")
    job_data = sheet.get_all_records()  # Fetch all jobs from Forming sheet
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
            row_data = add_timestamp(row_data, 12, "WIP-Tapping")  # Add timestamp for WIP Tapping
            sheet.append_row(row_data)  # Save to sheet
            st.success("บันทึกข้อมูลสำเร็จ!")

# Main app logic
def main():
    st.title("ระบบรับส่งงานระหว่างแผนกในโรงงาน")
    mode = st.sidebar.selectbox("เลือกโหมด", ['Forming', 'Tapping'])

    if mode == 'Forming':
        forming_mode()
    elif mode == 'Tapping':
        tapping_mode()

if __name__ == "__main__":
    main()
