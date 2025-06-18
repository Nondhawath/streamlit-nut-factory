import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ฟังก์ชั่นคำนวณผลต่างน้ำหนักและเปอร์เซ็นต์ความคลาดเคลื่อน
def calculate_weight_difference(weight_prev, weight_curr):
    return weight_curr - weight_prev, abs(weight_curr - weight_prev) / weight_prev * 100

# ฟังก์ชั่นเชื่อมต่อกับ Google Sheets
def connect_to_google_sheets():
    # ใช้สิทธิ์การเข้าถึง Google Sheets ด้วย OAuth 2.0
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

    # ใช้ข้อมูลจาก Streamlit Secrets เพื่อโหลดข้อมูล
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["google_cloud"], scope
    )

    # เชื่อมต่อกับ Google Sheets
    client = gspread.authorize(creds)

    # ใช้ ID ของไฟล์ Google Sheets แทนชื่อไฟล์
    sheet = client.open_by_key("1evJ6QuCW1jWmHbyD8pJCcRX8g3d_STWu94IOLY9LbXM").sheet1  # ใช้ Google Sheets ID

    return sheet

# สร้างฟอร์มให้ผู้ใช้กรอกข้อมูลน้ำหนัก
st.title('โปรแกรมเทียบข้อมูลน้ำหนัก')

# กรอกหมายเลข WOC
woc = st.text_input('กรอกหมายเลข Work Order Code (WOC)', '')

# เลือกแผนกก่อนหน้า
department_prev = st.selectbox("เลือกแผนกก่อนหน้า", ['Forming', 'Tapping'])

# เลือกแผนกปัจจุบัน
department_curr = st.selectbox("เลือกแผนกปัจจุบัน", ['Tapping', 'Final Inspection'])

# กรอกน้ำหนักจากแผนกก่อนหน้า
weight_prev = st.number_input(f'กรอกน้ำหนักจากแผนก {department_prev}', min_value=0.0, format="%.2f")

# กรอกน้ำหนักจากแผนกปัจจุบัน
weight_curr = st.number_input(f'กรอกน้ำหนักจากแผนก {department_curr}', min_value=0.0, format="%.2f")

# สร้างปุ่มตรวจสอบ
if st.button('ตรวจสอบ'):
    # ตรวจสอบว่าผู้ใช้กรอกข้อมูลหรือยัง
    if weight_prev > 0 and weight_curr > 0 and woc != "":
        # คำนวณผลต่างน้ำหนักและเปอร์เซ็นต์ความคลาดเคลื่อน
        weight_diff, percentage_diff = calculate_weight_difference(weight_prev, weight_curr)

        # แสดงผลต่างน้ำหนัก
        st.write(f"ผลต่างน้ำหนักระหว่างแผนก {department_prev} และ {department_curr}: {weight_diff:.2f} กิโลกรัม")
        
        # ตรวจสอบเปอร์เซ็นต์ความคลาดเคลื่อน
        if percentage_diff > 2:
            st.markdown('<p style="color:red; font-size:20px;">ค่าน้ำหนักไม่ถูกต้อง กรุณาเรียกหัวหน้างานเพื่อตรวจสอบ</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p style="color:green; font-size:20px;">น้ำหนักถูกต้อง ให้ปฏิบัติงานต่อได้</p>', unsafe_allow_html=True)
        
        # บันทึกข้อมูลลง Google Sheets
        sheet = connect_to_google_sheets()
        sheet.append_row([woc, department_prev, department_curr, weight_prev, weight_curr, weight_diff, percentage_diff])
        st.write("บันทึกข้อมูลลง Google Sheets เรียบร้อยแล้ว")
    else:
        st.write("กรุณากรอกหมายเลข WOC และน้ำหนักจากทั้งสองแผนกเพื่อทำการตรวจสอบ")
