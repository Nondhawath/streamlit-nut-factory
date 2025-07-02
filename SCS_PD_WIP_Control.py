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
wh_sheet = client.open_by_key(spreadsheet_id).worksheet('WH_Sheet')  # Warehouse
summary_sheet = client.open_by_key(spreadsheet_id).worksheet('Summary')  # ข้อมูลรวม
part_code_sheet = client.open_by_key(spreadsheet_id).worksheet('part_code_master')  # part_code_master

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

# ฟังก์ชันดึงข้อมูลรหัสงานจาก part_code_master
@st.cache_data
def get_part_codes():
    part_codes = part_code_sheet.col_values(1)  # ดึงข้อมูลจากคอลัมน์ "รหัสงาน"
    return part_codes

# Forming Mode
def forming_mode():
    st.header("Forming Mode (FM)")
    department_from = "FM"
    department_to = st.selectbox('แผนกปลายทาง', ['TP', 'FI', 'OS'])
    woc_number = st.text_input("หมายเลข WOC")
    
    # ดึงรายการรหัสงานจาก part_code_master
    part_codes = get_part_codes()  # ดึงข้อมูลรหัสงานจากชีท part_code_master
    part_name = st.selectbox("รหัสงาน / Part Name", part_codes)  # แสดงรายการรหัสงานให้เลือก
    
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
        # บันทึกข้อมูลลงในชีต FM
        row_data = [woc_number, part_name, "นายคมสันต์", department_from, department_to, lot_number, total_weight, barrel_weight, sample_weight, sample_count, pieces_count, "WIP-Forming"]
        row_data = add_timestamp(row_data)
        fm_sheet.append_row(row_data)
        st.success("บันทึกข้อมูลสำเร็จ!")
        send_telegram_message(f"Forming ส่งงานหมายเลข WOC {woc_number} ไปยัง {department_to}")

# Tapping Receive Mode (TP)
def tapping_receive_mode():
    st.header("Tapping Receive Mode (TP)")
    department_from = "FM"  # สำหรับกรณีรับงานจาก Forming
    department_to = "TP"
    
    # ดึงข้อมูลจาก FM ที่มีสถานะเป็น 'WIP-Forming'
    job_data = get_fm_data()  # ดึงข้อมูลจาก FM
    woc_data = [job for job in job_data if job['Status'] == 'WIP-Forming']  # กรอง WOC ที่สถานะเป็น WIP-Forming

    # แสดงรายการ WOC ที่สถานะเป็น 'WIP-Forming'
    woc_number = st.selectbox("เลือกหมายเลข WOC", [job['WOC Number'] for job in woc_data])

    # ค้นหาข้อมูลของ WOC ที่เลือก
    selected_job = next((job for job in woc_data if job['WOC Number'] == woc_number), None)
    if selected_job:
        part_name = selected_job['Part Name']
        lot_number = selected_job['Lot Number']
        total_weight = selected_job['Total Weight']
        barrel_weight = selected_job['Barrel Weight']
        sample_weight = selected_job['Sample Weight']
        sample_count = selected_job['Sample Count']
        pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)

        # แสดงข้อมูล WOC ที่เลือก
        st.write(f"Part Name: {part_name}")
        st.write(f"Lot Number: {lot_number}")
        st.write(f"Total Weight: {total_weight}")
        st.write(f"Barrel Weight: {barrel_weight}")
        st.write(f"Sample Weight: {sample_weight}")
        st.write(f"Sample Count: {sample_count}")
        st.write(f"Pieces Count: {pieces_count:.2f}")

    # รับงานเมื่อกดปุ่ม
    if st.button("รับงาน"):
        if selected_job:
            # อัปเดตสถานะใน FM เป็น "Tapping-Received"
            fm_row = next((job for job in woc_data if job['WOC Number'] == woc_number), None)  # หาค่า fm_row ที่ตรงกับ WOC
            if fm_row:
                # หาตำแหน่งของ WOC ใน FM sheet แล้วอัปเดตสถานะ
                cell = fm_sheet.find(woc_number)
                fm_sheet.update_cell(cell.row, cell.col + 1, "Tapping-Received")  # อัปเดตสถานะในคอลัมน์ Status
            st.success(f"รับงานหมายเลข {woc_number} สำเร็จ!")
            send_telegram_message(f"Tapping รับงานหมายเลข WOC {woc_number}")
        else:
            st.warning("กรุณาเลือก WOC และกรอกข้อมูลให้ครบถ้วน")

# Final Inspection Mode (Receive)
def final_inspection_receive_mode():
    st.header("Final Inspection Receive Mode (FI)")
    department_from = "TP"  # รับงานจาก Tapping
    department_to = "FI"
    job_data = get_tp_data()  # ดึงข้อมูลจาก TP
    woc_data = [job for job in job_data if job['Status'] == 'Tapping-Received']  # กรอง WOC ที่สถานะเป็น Tapping-Received
    woc_number = st.selectbox("เลือกหมายเลข WOC", [job['WOC Number'] for job in woc_data])
    
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
        
        # บันทึกข้อมูลลงในชีต FI
        row_data = [woc_number, "AP00002", "นายคมสันต์", department_from, department_to, "Lot124", total_weight, barrel_weight, sample_weight, sample_count, pieces_count, "Final Inspection-Received"]
        row_data = add_timestamp(row_data)
        fi_sheet.append_row(row_data)
        # เปลี่ยนสถานะใน TP เป็น "Final Inspection-Received"
        tp_row = [job for job in woc_data if job['WOC Number'] == woc_number][0]
        tp_sheet.update_cell(tp_row['row'], tp_sheet.find(woc_number).col, "Final Inspection-Received")
        st.success("รับงานจาก Tapping สำเร็จ!")
        send_telegram_message(f"Final Inspection รับงานหมายเลข WOC {woc_number}")

# Main function to run the app
def main():
    st.title("ระบบการโอนถ่ายงานระหว่างแผนก")
    mode = st.sidebar.selectbox("เลือกโหมด", ["Forming Mode", "Tapping Receive Mode", "Tapping Work Mode", "Final Inspection Receive Mode", "Final Work Mode", "TP Transfer Mode", "Completed Mode"])

    if mode == "Forming Mode":
        forming_mode()
    elif mode == "Tapping Receive Mode":
        tapping_receive_mode()
    elif mode == "Tapping Work Mode":
        pass  # Add functionality as needed
    elif mode == "Final Inspection Receive Mode":
        final_inspection_receive_mode()
    elif mode == "Final Work Mode":
        pass  # Add functionality as needed
    elif mode == "TP Transfer Mode":
        pass  # Add functionality as needed
    elif mode == "Completed Mode":
        pass  # Add functionality as needed

if __name__ == "__main__":
    main()
