import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# เรียกข้อมูลจาก Streamlit Secrets
google_credentials = st.secrets["google_credentials"]

# ตั้งค่าการเชื่อมต่อกับ Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_credentials, scope)
client = gspread.authorize(creds)

# เชื่อมต่อกับ Google Sheet โดยใช้ Spreadsheet ID
spreadsheet_id = "your_spreadsheet_id"  # เปลี่ยนเป็น Spreadsheet ID ที่คุณต้องการเข้าถึง
sheet = client.open_by_key(spreadsheet_id).sheet1  # เลือก sheet ที่ต้องการ

# ฟังก์ชันในการดึงข้อมูลจาก Google Sheet
def fetch_data_from_sheet():
    try:
        data = sheet.get_all_records()  # ดึงข้อมูลทั้งหมดจาก Google Sheets
        return data
    except Exception as e:
        st.error(f"Error reading data from Google Sheets: {e}")
        return []

# ฟังก์ชันเพื่อบันทึกข้อมูลใหม่
def save_data_to_sheet(data):
    try:
        sheet.append_row(data)  # เพิ่มแถวใหม่ไปยัง Google Sheets
        st.success("Data successfully saved!")
    except Exception as e:
        st.error(f"Error saving data to Google Sheets: {e}")

# สร้างฟังก์ชันหลัก
def main():
    st.title("Google Sheets API Example")

    # ดึงข้อมูลจาก Google Sheet
    data = fetch_data_from_sheet()

    # แสดงข้อมูลจาก Google Sheet
    st.write("Data from Google Sheets:")
    st.write(data)

    # แบบฟอร์มเพื่อบันทึกข้อมูลใหม่
    woc_number = st.text_input("WOC Number")
    part_name = st.text_input("Part Name")
    employee = st.text_input("Employee")
    department_from = st.text_input("Department From")
    department_to = st.text_input("Department To")
    lot_number = st.text_input("Lot Number")
    total_weight = st.number_input("Total Weight", min_value=0.0)
    barrel_weight = st.number_input("Barrel Weight", min_value=0.0)
    sample_weight = st.number_input("Sample Weight", min_value=0.0)
    sample_count = st.number_input("Sample Count", min_value=1)

    # คำนวณจำนวนชิ้นงาน
    pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)

    if st.button("Save Data"):
        # เก็บข้อมูลลงใน Google Sheets
        data_to_save = [woc_number, part_name, employee, department_from, department_to, lot_number, total_weight, barrel_weight, sample_weight, sample_count, pieces_count, "WIP-Forming", datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
        save_data_to_sheet(data_to_save)

if __name__ == "__main__":
    main()
