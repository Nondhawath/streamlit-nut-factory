import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime

# ตั้งค่าการเชื่อมต่อ Google Sheets
google_credentials = st.secrets["google_service_account"]  # ใช้ข้อมูลบัญชี Google จาก Secrets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# อนุญาตการเข้าถึงและตั้งค่า Client สำหรับการเชื่อมต่อ Google Sheets
def connect_google_sheets():
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(google_credentials, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อกับ Google Sheets: {e}")
        return None

# ฟังก์ชันสำหรับส่งข้อความ Telegram
def send_telegram_message(message):
    try:
        TELEGRAM_TOKEN = st.secrets["telegram_bot"]["telegram_bot_token"]
        CHAT_ID = st.secrets["telegram_bot"]["chat_id"]
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
        requests.get(url)
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการส่งข้อความ Telegram: {e}")

# ฟังก์ชันสำหรับเพิ่มเวลา Timestamp ในข้อมูล
def add_timestamp(row_data):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # เก็บเวลาในรูปแบบ YYYY-MM-DD HH:MM:SS
    row_data.append(timestamp)  # เพิ่ม Timestamp ลงในแถว
    return row_data

# ฟังก์ชันในการดึงข้อมูลจาก Google Sheets
def get_fm_data(client, spreadsheet_id):
    try:
        fm_sheet = client.open_by_key(spreadsheet_id).worksheet('FM_Sheet')
        return fm_sheet.get_all_records()  # ดึงข้อมูลจาก FM sheet
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูลจาก FM sheet: {e}")
        return []

def get_tp_data(client, spreadsheet_id):
    try:
        tp_sheet = client.open_by_key(spreadsheet_id).worksheet('TP_Sheet')
        return tp_sheet.get_all_records()  # ดึงข้อมูลจาก TP sheet
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูลจาก TP sheet: {e}")
        return []

def get_fi_data(client, spreadsheet_id):
    try:
        fi_sheet = client.open_by_key(spreadsheet_id).worksheet('FI_Sheet')
        return fi_sheet.get_all_records()  # ดึงข้อมูลจาก FI sheet
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูลจาก FI sheet: {e}")
        return []

def get_wh_data(client, spreadsheet_id):
    try:
        wh_sheet = client.open_by_key(spreadsheet_id).worksheet('WH_Sheet')
        return wh_sheet.get_all_records()  # ดึงข้อมูลจาก WH sheet
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูลจาก WH sheet: {e}")
        return []

# Forming Mode
def forming_mode(client, spreadsheet_id):
    st.header("Forming Mode (FM)")
    department_from = "FM"
    department_to = st.selectbox('แผนกปลายทาง', ['TP', 'FI', 'OS'])
    woc_number = st.text_input("หมายเลข WOC")
    part_name = st.selectbox("รหัสงาน / Part Name", ["Part 1", "Part 2", "Part 3"])  # เปลี่ยนเป็นการดึงข้อมูลจากชีต
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
        try:
            fm_sheet = client.open_by_key(spreadsheet_id).worksheet('FM_Sheet')
            row_data = [woc_number, part_name, "นายคมสันต์", department_from, department_to, lot_number, total_weight, barrel_weight, sample_weight, sample_count, pieces_count, "WIP-Forming"]
            row_data = add_timestamp(row_data)
            fm_sheet.append_row(row_data)
            st.success("บันทึกข้อมูลสำเร็จ!")
            send_telegram_message(f"Forming ส่งงานหมายเลข WOC {woc_number} ไปยัง {department_to}")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการบันทึกข้อมูล: {e}")

# Tapping Work Mode
def tapping_work_mode(client, spreadsheet_id):
    st.header("Tapping Work Mode")
    woc_number = st.text_input("หมายเลข WOC ที่ต้องการทำงาน")
    machine_name = st.selectbox("เลือกชื่อเครื่อง", ["เครื่อง 1", "เครื่อง 2", "เครื่อง 3"])  # เปลี่ยนให้ดึงข้อมูลจาก Google Sheets
    if st.button("เริ่มทำงาน"):
        try:
            tp_sheet = client.open_by_key(spreadsheet_id).worksheet('TP_Sheet')
            row_data = [woc_number, machine_name, "นายคมสันต์", "TP", "FI", "Lot123", 1000, 200, 100, 10, 50, "Work-Tapping"]
            row_data = add_timestamp(row_data)
            tp_sheet.append_row(row_data)
            st.success("ทำงานใน Tapping สำเร็จ!")
            send_telegram_message(f"Tapping Work on WOC {woc_number} at {machine_name}")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการบันทึกข้อมูล: {e}")

# Final Work Mode
def final_work_mode(client, spreadsheet_id):
    st.header("Final Work Mode")
    woc_number = st.text_input("หมายเลข WOC ที่ต้องการทำงาน")
    machine_name = st.selectbox("เลือกชื่อเครื่อง", ["เครื่อง 1", "เครื่อง 2", "เครื่อง 3"])  # เปลี่ยนให้ดึงข้อมูลจาก Google Sheets
    if st.button("เริ่มทำงาน"):
        try:
            fi_sheet = client.open_by_key(spreadsheet_id).worksheet('FI_Sheet')
            row_data = [woc_number, machine_name, "นายคมสันต์", "FI", "WH", "Lot123", 1000, 200, 100, 10, 50, "Work-Final Inspection"]
            row_data = add_timestamp(row_data)
            fi_sheet.append_row(row_data)
            st.success("ทำงานใน Final Inspection สำเร็จ!")
            send_telegram_message(f"Final Inspection Work on WOC {woc_number} at {machine_name}")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการบันทึกข้อมูล: {e}")

# TP Transfer Mode
def tp_transfer_mode(client, spreadsheet_id):
    st.header("TP Transfer Mode")
    woc_number = st.text_input("หมายเลข WOC ที่จะโอน")
    department_from = st.selectbox("เลือกแผนกต้นทาง", ["TP", "FI", "OS"])
    department_to = st.selectbox("เลือกแผนกปลายทาง", ["FI", "OS", "WH"])
    if st.button("โอนงาน"):
        try:
            tp_sheet = client.open_by_key(spreadsheet_id).worksheet('TP_Sheet')
            row_data = [woc_number, "เครื่อง 1", "นายคมสันต์", department_from, department_to, "Lot123", 1000, 200, 100, 10, 50, "Transfer"]
            row_data = add_timestamp(row_data)
            tp_sheet.append_row(row_data)
            st.success(f"โอนงานจาก {department_from} ไปยัง {department_to} สำเร็จ!")
            send_telegram_message(f"Transfer WOC {woc_number} from {department_from} to {department_to}")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการโอนงาน: {e}")

# Completed Mode
def completed_mode(client, spreadsheet_id):
    st.header("Completed Mode")
    woc_number = st.text_input("หมายเลข WOC ที่เสร็จสมบูรณ์")
    if st.button("บันทึกงานที่เสร็จสมบูรณ์"):
        try:
            wh_sheet = client.open_by_key(spreadsheet_id).worksheet('WH_Sheet')
            row_data = [woc_number, "นายคมสันต์", "WH", "Lot123", 1000, 200, 100, 10, 50, "Completed"]
            row_data = add_timestamp(row_data)
            wh_sheet.append_row(row_data)
            st.success(f"บันทึกงานที่เสร็จสมบูรณ์หมายเลข WOC {woc_number} สำเร็จ!")
            send_telegram_message(f"Completed WOC {woc_number} and sent to Warehouse")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการบันทึกงานที่เสร็จสมบูรณ์: {e}")

# Main function to run the app
def main():
    st.title("ระบบการโอนถ่ายงานระหว่างแผนก")
    client = connect_google_sheets()
    if not client:
        return  # If cannot connect to Google Sheets, stop the app

    spreadsheet_id = '1GbHXO0d2GNXEwEZfeygGqNEBRQJQUoC_MO1mA-389gE'  # ใส่ Spreadsheet ID ที่คุณใช้งาน
    mode = st.sidebar.selectbox("เลือกโหมด", ["Forming Mode", "Tapping Receive Mode", "Tapping Work Mode", "Final Inspection Receive Mode", "Final Work Mode", "TP Transfer Mode", "Completed Mode"])

    if mode == "Forming Mode":
        forming_mode(client, spreadsheet_id)
    elif mode == "Tapping Receive Mode":
        tapping_mode(client, spreadsheet_id)
    elif mode == "Tapping Work Mode":
        tapping_work_mode(client, spreadsheet_id)
    elif mode == "Final Inspection Receive Mode":
        final_inspection_mode(client, spreadsheet_id)
    elif mode == "Final Work Mode":
        final_work_mode(client, spreadsheet_id)
    elif mode == "TP Transfer Mode":
        tp_transfer_mode(client, spreadsheet_id)
    elif mode == "Completed Mode":
        completed_mode(client, spreadsheet_id)

if __name__ == "__main__":
    main()
