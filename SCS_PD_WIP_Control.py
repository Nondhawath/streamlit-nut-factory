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

# ฟังก์ชันในการดึงข้อมูลจาก Google Sheets โดยใช้ Cache เพื่อป้องกันการดึงข้อมูลซ้ำ
@st.cache_data
def get_fm_data(client, spreadsheet_id):
    try:
        fm_sheet = client.open_by_key(spreadsheet_id).worksheet('FM_Sheet')
        return fm_sheet.get_all_records()  # ดึงข้อมูลจาก FM sheet
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูลจาก FM sheet: {e}")
        return []

@st.cache_data
def get_tp_data(client, spreadsheet_id):
    try:
        tp_sheet = client.open_by_key(spreadsheet_id).worksheet('TP_Sheet')
        return tp_sheet.get_all_records()  # ดึงข้อมูลจาก TP sheet
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูลจาก TP sheet: {e}")
        return []

@st.cache_data
def get_fi_data(client, spreadsheet_id):
    try:
        fi_sheet = client.open_by_key(spreadsheet_id).worksheet('FI_Sheet')
        return fi_sheet.get_all_records()  # ดึงข้อมูลจาก FI sheet
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูลจาก FI sheet: {e}")
        return []

@st.cache_data
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

# Tapping Mode
def tapping_mode(client, spreadsheet_id):
    st.header("Tapping Receive Mode (TP)")
    department_from = "FM"  # สำหรับกรณีรับงานจาก Forming
    department_to = "TP"
    job_data = get_fm_data(client, spreadsheet_id)  # ดึงข้อมูลจาก FM
    woc_number = st.selectbox("เลือกหมายเลข WOC", [job['WOC Number'] for job in job_data])
    
    # กรอกข้อมูลการรับ
    total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
    barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
    sample_weight = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1)

    if st.button("รับงาน"):
        # คำนวณจำนวนชิ้นงาน
        if total_weight and barrel_weight and sample_weight and sample_count:
            pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)
            st.write(f"จำนวนชิ้นงาน: {pieces_count:.2f}")
        
        try:
            tp_sheet = client.open_by_key(spreadsheet_id).worksheet('TP_Sheet')
            row_data = [woc_number, "AP00001", "นายคมสันต์", department_from, department_to, "Lot123", total_weight, barrel_weight, sample_weight, sample_count, pieces_count, "WIP-Tapping"]
            row_data = add_timestamp(row_data)
            tp_sheet.append_row(row_data)
            st.success("รับงานสำเร็จ!")
            send_telegram_message(f"Tapping รับงานหมายเลข WOC {woc_number}")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการบันทึกข้อมูล: {e}")

# Final Inspection Mode
def final_inspection_mode(client, spreadsheet_id):
    st.header("Final Inspection Receive Mode (FI)")
    department_from = "TP"  # รับงานจาก Tapping
    department_to = "FI"
    job_data = get_tp_data(client, spreadsheet_id)  # ดึงข้อมูลจาก TP
    woc_number = st.selectbox("เลือกหมายเลข WOC", [job['WOC Number'] for job in job_data])
    
    # กรอกข้อมูลการรับ
    total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
    barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
    sample_weight = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1)

    if st.button("รับงาน"):
        # คำนวณจำนวนชิ้นงาน
        if total_weight and barrel_weight and sample_weight and sample_count:
            pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)
            st.write(f"จำนวนชิ้นงาน: {pieces_count:.2f}")
        
        try:
            fi_sheet = client.open_by_key(spreadsheet_id).worksheet('FI_Sheet')
            row_data = [woc_number, "AP00002", "นายคมสันต์", department_from, department_to, "Lot124", total_weight, barrel_weight, sample_weight, sample_count, pieces_count, "WIP-Final Inspection"]
            row_data = add_timestamp(row_data)
            fi_sheet.append_row(row_data)
            st.success("รับงานจาก Tapping สำเร็จ!")
            send_telegram_message(f"Final Inspection รับงานหมายเลข WOC {woc_number}")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการบันทึกข้อมูล: {e}")

# Main function to run the app
def main():
    st.title("ระบบการโอนถ่ายงานระหว่างแผนก")
    client = connect_google_sheets()
    if client is None:
        return
    
    spreadsheet_id = '1GbHXO0d2GNXEwEZfeygGqNEBRQJQUoC_MO1mA-389gE'  # ใส่ Spreadsheet ID ที่คุณใช้งาน
    mode = st.sidebar.selectbox("เลือกโหมด", ["Forming Mode", "Tapping Receive Mode", "Tapping Work Mode", "Final Inspection Receive Mode", "Final Work Mode", "TP Transfer Mode", "Completed Mode"])

    if mode == "Forming Mode":
        forming_mode(client, spreadsheet_id)
    elif mode == "Tapping Receive Mode":
        tapping_mode(client, spreadsheet_id)
    elif mode == "Tapping Work Mode":
        st.write("Tapping Work Mode")
    elif mode == "Final Inspection Receive Mode":
        final_inspection_mode(client, spreadsheet_id)
    elif mode == "Final Work Mode":
        st.write("Final Work Mode")
    elif mode == "TP Transfer Mode":
        st.write("TP Transfer Mode")
    elif mode == "Completed Mode":
        st.write("Completed Mode")

if __name__ == "__main__":
    main()
