import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Setup Google Sheets connection
google_credentials = st.secrets["google_service_account"]

# Define the scope for Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Authorize the credentials and set up the client
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_credentials, scope)
client = gspread.authorize(creds)

# Use Spreadsheet ID
spreadsheet_id = '1GbHXO0d2GNXEwEZfeygGqNEBRQJQUoC_MO1mA-389gE'

# Add status and timestamp function
def add_status_timestamp(row_data, status_column_index, status_value):
    timestamp = datetime.now().strftime('%d-%m-%Y %H:%M')
    row_data[status_column_index] = status_value
    row_data[status_column_index + 1] = timestamp
    return row_data

# Forming Mode (FM)
def forming_mode():
    st.header("Forming Mode")
    department_from = "Forming"
    department_to = st.selectbox('เลือกแผนกปลายทาง', ['Tapping', 'Final Inspection', 'Outsource'])
    woc_number = st.text_input("หมายเลข WOC")
    woc_new = st.text_input("หมายเลข WOC ใหม่ (สำหรับแผนกปลายทาง)")
    part_name = st.selectbox("รหัสงาน / Part Name", ["Part A", "Part B", "Part C"])  # Example
    lot_number = st.text_input("หมายเลข LOT")
    total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
    barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
    sample_weight = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1)

    if total_weight and barrel_weight and sample_weight and sample_count:
        pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)
        st.write(f"จำนวนชิ้นงาน: {pieces_count:.2f}")

    if st.button("บันทึก"):
        row_data = [woc_number, part_name, 'นายคมสันต์ คงคำลี', department_from, department_to, lot_number, total_weight, barrel_weight, sample_weight, sample_count, pieces_count, woc_new]
        row_data = add_status_timestamp(row_data, 11, "WIP-Forming")
        sheet = client.open_by_key(spreadsheet_id).worksheet('FM')  # Save to "FM" sheet
        sheet.append_row(row_data)
        st.success("บันทึกข้อมูลสำเร็จ!")

# Tapping Mode (TP)
def tapping_mode():
    st.header("Tapping Mode")
    woc_number = st.selectbox("เลือกหมายเลข WOC จากที่ส่งมา", ['WOC001', 'WOC002'])
    woc_new = st.text_input("หมายเลข WOC ใหม่ (สำหรับแผนกปลายทาง)")
    total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
    barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
    sample_weight = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1)

    if total_weight and barrel_weight and sample_weight and sample_count:
        pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)
        st.write(f"จำนวนชิ้นงาน: {pieces_count:.2f}")

    if st.button("บันทึก"):
        row_data = [woc_number, 'Tapping Work', total_weight, barrel_weight, sample_weight, sample_count, pieces_count, woc_new]
        row_data = add_status_timestamp(row_data, 11, "WIP-Tapping")
        sheet = client.open_by_key(spreadsheet_id).worksheet('TP')  # Save to "TP" sheet
        sheet.append_row(row_data)
        st.success(f"บันทึกข้อมูลสำเร็จสำหรับ WOC {woc_number}!")

# Work Mode (Work)
def work_mode():
    st.header("Work Mode")
    woc_number = st.selectbox("ค้นหาหมายเลข WOC", ['WOC001', 'WOC002'])
    machine_name = st.selectbox("เลือกชื่อเครื่องจักร", ['TP-01', 'TP-02'])

    if st.button("เริ่มทำงาน"):
        row_data = [woc_number, machine_name]
        row_data = add_status_timestamp(row_data, 11, "WIP-Work")
        sheet = client.open_by_key(spreadsheet_id).worksheet('WO')  # Save to "WO" sheet
        sheet.append_row(row_data)
        st.success(f"เริ่มทำงานที่เครื่อง {machine_name} เสร็จสิ้น!")

# Main app logic
def main():
    st.title("ระบบการรับส่งงานระหว่างแผนกในโรงงาน")
    mode = st.sidebar.selectbox("เลือกโหมด", ['Forming', 'Tapping', 'Work'])

    if mode == 'Forming':
        forming_mode()
    elif mode == 'Tapping':
        tapping_mode()
    elif mode == 'Work':
        work_mode()

if __name__ == "__main__":
    main()
