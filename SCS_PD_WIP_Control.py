import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime
import pytz

# ตั้งค่าการเชื่อมต่อกับ Google Sheets
google_credentials = st.secrets["google_service_account"]  # ดึงข้อมูล credentials จาก secrets

# กำหนด scope สำหรับ Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# อนุมัติการเข้าถึงข้อมูล Google Sheets
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_credentials, scope)

# เชื่อมต่อกับ Google Sheets
try:
    client = gspread.authorize(creds)
    # ระบุ Spreadsheet ID ของคุณ
    sheet = client.open_by_key('1GbHXO0d2GNXEwEZfeygGqNEBRQJQUoC_MO1mA-389gE').worksheet('Jobs')
    part_code_master_sheet = client.open_by_key('1GbHXO0d2GNXEwEZfeygGqNEBRQJQUoC_MO1mA-389gE').worksheet('part_code_master')
    employees_sheet = client.open_by_key('1GbHXO0d2GNXEwEZfeygGqNEBRQJQUoC_MO1mA-389gE').worksheet('Employees')
except gspread.exceptions.GSpreadException as e:
    st.error(f"Error connecting to Google Sheets: {e}")
    raise

# ฟังก์ชันการส่งข้อความผ่าน Telegram
def send_telegram_message(message):
    TELEGRAM_TOKEN = st.secrets["telegram"]["telegram_bot_token"]  # ดึง token จาก secrets
    CHAT_ID = st.secrets["telegram"]["chat_id"]  # ดึง chat_id จาก secrets

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    requests.get(url)

# ฟังก์ชันดึงรหัสงานจาก Google Sheets
@st.cache_data(ttl=60*10)  # Cache for 10 minutes
def get_part_codes():
    try:
        part_codes = part_code_master_sheet.col_values(1)  # ดึงรหัสงานจากคอลัมน์แรก
        return part_codes
    except Exception as e:
        st.error(f"Error fetching part codes: {e}")
        return []

# ฟังก์ชันเพิ่ม status และ timestamp
def add_status_timestamp(row_data, status_column_index, status_value):
    # เช็คให้แน่ใจว่า row_data มีจำนวนคอลัมน์ที่เพียงพอ
    while len(row_data) <= status_column_index + 1:
        row_data.append('')  # เพิ่มคอลัมน์ว่างถ้ายังไม่พอ

    tz = pytz.timezone('Asia/Bangkok')  # ตั้งเวลาเป็นเวลาในประเทศไทย
    timestamp = datetime.now(tz).strftime('%d-%m-%Y %H:%M')  # เวลาปัจจุบันในรูปแบบที่ต้องการ

    # อัปเดตสถานะและ timestamp
    row_data[status_column_index] = status_value
    row_data[status_column_index + 1] = timestamp  # เพิ่ม timestamp ในคอลัมน์ถัดไป

    return row_data

# ฟังก์ชันเพื่อหาบรรทัดที่มี WOC ที่ต้องการ
def find_woc_row(woc_number):
    try:
        job_data = sheet.get_all_records()  # ดึงข้อมูลงานทั้งหมดจาก Google Sheets
        for idx, job in enumerate(job_data):
            if job.get("WOC Number") == woc_number:  # ถ้าหมายเลข WOC ตรง
                return idx + 2  # คืนค่าบรรทัดที่พบ (gspread ใช้เลขบรรทัดเริ่มต้นที่ 1)
        return None  # ถ้าไม่พบ WOC ที่ตรงกัน
    except Exception as e:
        st.error(f"Error finding WOC row: {e}")
        return None

# ฟังก์ชันอัปเดตข้อมูลใน Google Sheets
def update_woc_row(woc_number, row_data):
    row = find_woc_row(woc_number)
    if row:
        current_row_data = sheet.row_values(row)

        # ตรวจสอบให้แน่ใจว่า row_data มีขนาดพอๆ กับ current_row_data
        if len(current_row_data) < 16:
            current_row_data += [''] * (16 - len(current_row_data))

        # อัปเดตข้อมูลในแต่ละคอลัมน์
        current_row_data[0] = row_data[0]  # WOC Number
        current_row_data[1] = row_data[1]  # Part Name
        current_row_data[2] = row_data[2]  # Employee
        current_row_data[3] = row_data[3]  # Department From
        current_row_data[4] = row_data[4]  # Department To
        current_row_data[5] = row_data[5]  # Lot Number
        current_row_data[6] = row_data[6]  # Total Weight
        current_row_data[7] = row_data[7]  # Barrel Weight
        current_row_data[8] = row_data[8]  # Sample Weight
        current_row_data[9] = row_data[9]  # Sample Count
        current_row_data[10] = row_data[10]  # Pieces Count
        current_row_data[11] = row_data[11]  # WIP Forming
        current_row_data[12] = row_data[12]  # Timestamp
        current_row_data[13] = row_data[13]  # WIP Tapping
        current_row_data[14] = row_data[14]  # WIP Final Inspection
        current_row_data[15] = row_data[15]  # WIP Final Work

        # อัปเดตแถวใน Google Sheets
        sheet.update(f"A{row}:P{row}", [current_row_data])  # อัปเดตทั้งแถว
    else:
        # ถ้าไม่พบ WOC ให้เพิ่มแถวใหม่
        sheet.append_row(row_data)  # เพิ่มแถวใหม่

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
        # Add status and timestamp for WIP-Forming
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
            st.write(f"จำนวนชิ้นงานแตกต่างกัน: {difference:.2f}")

            row_data = [job_woc, pieces_count, difference, "WIP-Tapping"]
            row_data = add_status_timestamp(row_data, 13, "WIP-Tapping")  # Add timestamp to the row
            update_woc_row(job_woc, row_data)  # Update the job status in Google Sheets
            st.success("บันทึกข้อมูลสำเร็จ!")
            send_telegram_message(f"Job WOC {job_woc} processed in Tapping")

# Main function
def main():
    st.sidebar.title("เลือกโหมด")
    mode = st.sidebar.selectbox("เลือกโหมด", ['Forming', 'Tapping', 'Final Inspection', 'Final Work', 'TP Transfer'])

    if mode == 'Forming':
        forming_mode()
    elif mode == 'Tapping':
        tapping_mode()
    # Add more modes if needed (e.g., Final Inspection, Final Work, TP Transfer)

if __name__ == "__main__":
    main()
