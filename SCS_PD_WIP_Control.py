import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime

# ตั้งค่าการเชื่อมต่อ Google Sheets
google_credentials = st.secrets["google_service_account"]  # ใช้ข้อมูลบัญชี Google จาก Secrets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# อนุญาตการเข้าถึงและตั้งค่า Client สำหรับการเชื่อมต่อ Google Sheets
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_credentials, scope)
client = gspread.authorize(creds)

# ตั้งชื่อไฟล์ Google Sheets ที่จะใช้
spreadsheet_id = '1GbHXO0d2GNXEwEZfeygGqNEBRQJQUoC_MO1mA-389gE'  # ใส่ Spreadsheet ID ที่คุณใช้งาน

# เข้าถึงชีตต่าง ๆ ตามแผนกที่กำหนด
fm_sheet = client.open_by_key(spreadsheet_id).worksheet('FM_Sheet')  # Forming
tp_sheet = client.open_by_key(spreadsheet_id).worksheet('TP_Sheet')  # Tapping
fi_sheet = client.open_by_key(spreadsheet_id).worksheet('FI_Sheet')  # Final Inspection

# Telegram bot สำหรับการแจ้งเตือน
TELEGRAM_TOKEN = st.secrets["telegram_bot"]["telegram_bot_token"]
CHAT_ID = st.secrets["telegram_bot"]["chat_id"]

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    requests.get(url)

# ฟังก์ชันสำหรับเพิ่มเวลา Timestamp ในข้อมูล
def add_timestamp(row_data):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # เก็บเวลาในรูปแบบ YYYY-MM-DD HH:MM:SS
    row_data.append(timestamp)  # เพิ่ม Timestamp ลงในแถว
    return row_data

# ฟังก์ชันดึงข้อมูลจาก Google Sheets และแคชข้อมูลเพื่อป้องกันการดึงข้อมูลบ่อยเกินไป
@st.cache_data
def get_fm_data():
    return fm_sheet.get_all_records()  # ดึงข้อมูลจาก FM sheet

@st.cache_data
def get_tp_data():
    return tp_sheet.get_all_records()  # ดึงข้อมูลจาก TP sheet

@st.cache_data
def get_fi_data():
    return fi_sheet.get_all_records()  # ดึงข้อมูลจาก FI sheet

# ฟังก์ชันดึงข้อมูลพนักงานจากชีท Employees
def get_employees_data():
    employees_sheet = client.open_by_key(spreadsheet_id).worksheet('Employees')
    return employees_sheet.get_all_records()

# ฟังก์ชันดึงข้อมูลรหัสงานจากชีท part_code_master
def get_part_codes():
    part_code_sheet = client.open_by_key(spreadsheet_id).worksheet('part_code_master')
    return part_code_sheet.get_all_records()

# ฟังก์ชัน login
def login():
    # ดึงข้อมูลพนักงานจาก Google Sheets
    employees = get_employees_data()

    # แสดงข้อมูลที่ดึงมาเพื่อการตรวจสอบ
    # st.write("Employee Data:", employees)  # แสดงข้อมูลพนักงานที่ดึงจาก Google Sheets

    # ตรวจสอบคอลัมน์ที่ถูกต้องใน Google Sheets
    try:
        employee_names = []
        employee_ids = {}

        # ตรวจสอบว่าในข้อมูลพนักงานมีคอลัมน์ 'ชื่อพนักงาน' และ 'รหัสพนักงาน' โดยให้เฉพาะแถวที่มีข้อมูลครบถ้วน
        for emp in employees:
            # ตรวจสอบว่าแถวมีทั้ง 'ชื่อพนักงาน' และ 'รหัสพนักงาน'
            if 'ชื่อพนักงาน' in emp and 'รหัสพนักงาน' in emp:
                # ตรวจสอบว่าไม่มีค่าเป็น None หรือ ค่าว่างใน 'ชื่อพนักงาน' และ 'รหัสพนักงาน'
                if emp['ชื่อพนักงาน'] and emp['รหัสพนักงาน']:
                    employee_names.append(emp['ชื่อพนักงาน'].strip())  # คัดเลือกชื่อพนักงานและตัดช่องว่าง
                    employee_ids[emp['ชื่อพนักงาน'].strip()] = emp['รหัสพนักงาน'].strip()  # สร้าง dictionary ที่เก็บชื่อพนักงานและรหัสพนักงาน พร้อมตัดช่องว่าง
                else:
                    st.warning(f"ข้อมูลพนักงาน '{emp['ชื่อพนักงาน']}' ขาดข้อมูลบางส่วน!")
            else:
                st.warning("ข้อมูลพนักงานไม่สมบูรณ์: ไม่มีคอลัมน์ 'ชื่อพนักงาน' หรือ 'รหัสพนักงาน'")

        if not employee_names or not employee_ids:
            st.error("ไม่มีข้อมูลพนักงานที่ถูกต้อง!")
            return None, None

    except KeyError as e:
        st.error(f"Error: คอลัมน์ใน Google Sheets ไม่ตรงกัน - {e}")
        return None, None  # หากไม่พบคอลัมน์ที่ต้องการ

    # ดึงข้อมูลรหัสงานจาก part_code_master
    part_codes = get_part_codes()
    part_names = [part['รหัสงาน'] for part in part_codes]  # คัดเลือกรหัสงาน

    # UI สำหรับเลือกพนักงานและรหัสงาน
    st.header("Login")
    employee_name = st.selectbox("เลือกชื่อพนักงาน", employee_names)
    employee_id = st.text_input("กรอก Employee ID")

    login_button = st.button("Login")

    # เช็คการ login ของพนักงานเมื่อกดปุ่ม
    if login_button:
        # ตัดช่องว่างจากชื่อพนักงานและรหัสพนักงานทั้งสอง
        employee_name = employee_name.strip()
        employee_id = employee_id.strip()

        # ตรวจสอบว่า Employee ID ตรงกับที่บันทึกใน Google Sheets
        if employee_ids.get(employee_name) == employee_id:
            st.success(f"Login สำเร็จ! ยินดีต้อนรับ, {employee_name}")
            part_code = st.selectbox("เลือก รหัสงาน", part_names)  # ให้เลือก รหัสงาน เมื่อ login สำเร็จ
            return employee_name, part_code
        else:
            st.error("รหัสพนักงานไม่ถูกต้อง!")
    return None, None  # เมื่อยังไม่ได้ login

# Forming Mode
def forming_mode(employee_name, part_code):
    st.header("Forming Mode (FM)")
    st.write(f"พนักงานที่ทำการบันทึก: {employee_name}")
    st.write(f"รหัสงานที่เลือก: {part_code}")

    # ฟอร์มการกรอกข้อมูล
    department_from = "FM"
    department_to = st.selectbox('แผนกปลายทาง', ['TP', 'FI', 'OS'])
    woc_number = st.text_input("หมายเลข WOC")
    lot_number = st.text_input("หมายเลข LOT")
    total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
    barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
    sample_weight = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1)

    # คำนวณจำนวนชิ้นงาน
    if total_weight and barrel_weight and sample_weight and sample_count:
        pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)
        st.write(f"จำนวนชิ้นงาน: {pieces_count:.2f}")
    
    if st.button("บันทึก"):
        row_data = [woc_number, part_code, employee_name, department_from, department_to, lot_number, total_weight, barrel_weight, sample_weight, sample_count, pieces_count, "WIP-Forming"]
        row_data = add_timestamp(row_data)
        fm_sheet.append_row(row_data)
        st.success("บันทึกข้อมูลสำเร็จ!")
        send_telegram_message(f"Forming ส่งงานหมายเลข WOC {woc_number} ไปยัง {department_to}")

# Main function to run the app
def main():
    st.title("ระบบการโอนถ่ายงานระหว่างแผนก")

    # การ login
    employee_name, part_code = login()

    if employee_name and part_code:
        # เมื่อ login สำเร็จ
        mode = st.sidebar.selectbox("เลือกโหมด", ["Forming Mode"])

        if mode == "Forming Mode":
            forming_mode(employee_name, part_code)  # ส่งพนักงานและรหัสงานไปที่ฟังก์ชัน Forming Mode

if __name__ == "__main__":
    main()
