import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Set up Google Sheets connection
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["google_service_account"], scope)
client = gspread.authorize(creds)

# Define Google Sheets
spreadsheet_id = '1GbHXO0d2GNXEwEZfeygGqNEBRQJQUoC_MO1mA-389gE'

# Sheets for each department
fm_sheet = client.open_by_key(spreadsheet_id).worksheet('FM_Sheet')  # Forming Sheet
tp_sheet = client.open_by_key(spreadsheet_id).worksheet('TP_Sheet')  # Tapping Sheet
fi_sheet = client.open_by_key(spreadsheet_id).worksheet('FI_Sheet')  # Final Inspection Sheet
wh_sheet = client.open_by_key(spreadsheet_id).worksheet('WH_Sheet')  # Warehouse Sheet
summary_sheet = client.open_by_key(spreadsheet_id).worksheet('Summary')  # Summary Sheet

# Function to get part names from the Part Code Master Sheet
def get_part_names():
    part_code_master_sheet = client.open_by_key(spreadsheet_id).worksheet('part_code_master')
    part_code_master_data = part_code_master_sheet.get_all_records()
    return [part['รหัสงาน'] for part in part_code_master_data]

# Function to get employees
def get_employees():
    employees_sheet = client.open_by_key(spreadsheet_id).worksheet('Employees')
    employees_data = employees_sheet.get_all_records()
    return [employee['ชื่อพนักงาน'] for employee in employees_data]

# Function to get machine names
def get_machines():
    machines_sheet = client.open_by_key(spreadsheet_id).worksheet('Machines')
    machines_data = machines_sheet.get_all_records()
    return [machine['Machine Name'] for machine in machines_data]

# Function to add timestamp
def add_timestamp(row_data, status_column_index, status_value):
    row_data[status_column_index] = status_value  # Add the status to the row
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    row_data.append(timestamp)  # Add timestamp to the row
    return row_data

# Forming Mode
def forming_mode():
    st.header("Forming Mode (FM)")
    department_from = "Forming"
    department_to = st.selectbox('เลือกแผนกปลายทาง', ['Tapping', 'Final Inspection', 'Out Source'])
    woc_number = st.text_input("หมายเลข WOC")
    part_name = st.selectbox("รหัสงาน / Part Name", get_part_names())
    employee = st.selectbox("ชื่อพนักงาน", get_employees())
    lot_number = st.text_input("หมายเลข LOT")
    total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
    barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
    sample_weight = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1)

    # Calculate pieces count
    if total_weight and barrel_weight and sample_weight and sample_count:
        pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)
        st.write(f"จำนวนชิ้นงาน: {pieces_count:.2f}")
    
    if st.button("บันทึก"):
        row_data = [woc_number, part_name, employee, department_from, department_to, lot_number, total_weight, barrel_weight, sample_weight, sample_count, pieces_count]
        row_data = add_timestamp(row_data, 11, "WIP-Forming")
        fm_sheet.append_row(row_data)
        summary_sheet.append_row(row_data)  # Save to summary sheet as well
        st.success("บันทึกข้อมูลสำเร็จ!")

# Tapping Mode
def tapping_mode():
    st.header("Tapping Mode (TP)")
    job_data = summary_sheet.get_all_records()  # Fetch all jobs from Summary Sheet
    woc_number = st.selectbox("เลือกหมายเลข WOC", [job['WOC Number'] for job in job_data])
    job = next(job for job in job_data if job['WOC Number'] == woc_number)

    if job:
        st.write(f"ข้อมูลงาน: {job}")
        total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
        barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
        sample_weight = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0)
        sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1)

        if total_weight and barrel_weight and sample_weight and sample_count:
            pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)
            st.write(f"จำนวนชิ้นงาน: {pieces_count:.2f}")

        if st.button("คำนวณและเปรียบเทียบ"):
            # Compare with Forming mode pieces count
            forming_pieces_count = job['Pieces Count']
            difference = abs(pieces_count - forming_pieces_count) / forming_pieces_count * 100
            st.write(f"จำนวนชิ้นงานแตกต่างกัน: {difference:.2f}%")
            row_data = [woc_number, pieces_count, difference]
            row_data = add_timestamp(row_data, 12, "WIP-Tapping")
            tp_sheet.append_row(row_data)
            summary_sheet.append_row(row_data)  # Save to summary sheet as well
            st.success("บันทึกข้อมูลสำเร็จ!")

# Main app logic
def main():
    st.title("ระบบการโอนถ่ายงานระหว่างแผนก")
    mode = st.sidebar.selectbox("เลือกโหมด", ['Forming Mode', 'Tapping Mode'])

    if mode == 'Forming Mode':
        forming_mode()
    elif mode == 'Tapping Mode':
        tapping_mode()

if __name__ == "__main__":
    main()
