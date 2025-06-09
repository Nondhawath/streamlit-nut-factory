import streamlit as st
import pygsheets
import json

# ดึงข้อมูล Google API Credentials จาก Streamlit Secrets
google_credentials = st.secrets["gcp_service_account"]

# บันทึกไฟล์ JSON ของ Credentials ไว้ในไฟล์ชั่วคราว
with open("/tmp/google-api-credentials.json", "w") as f:
    f.write(json.dumps(google_credentials))

# เชื่อมต่อกับ Google Sheets โดยใช้ไฟล์ credentials
gc = pygsheets.authorize(service_file='/tmp/google-api-credentials.json')

# เปิดไฟล์ Google Sheets
sh = gc.open('Assign_Job_FI')

# อ่านข้อมูลจาก Google Sheets
worksheet = sh.worksheet('title', 'Machines')
machines_data = worksheet.get_all_records()

# แสดงข้อมูลเครื่องจักรใน Streamlit
st.title("Machine List")
st.write(machines_data)

# ฟอร์มการอัปโหลดแผนงาน
st.subheader("Upload Plan")

# ให้ผู้ใช้กรอกข้อมูลแผนงาน
job_name = st.text_input("Job Name")
quantity = st.number_input("Quantity", min_value=1)
delivery_date = st.date_input("Delivery Date", min_value=datetime.today())

# การอัปโหลดแผนงานไปยัง Google Sheets
if st.button("Upload Plan"):
    plan_data = {
        'Job Name': job_name,
        'Quantity': quantity,
        'Delivery Date': str(delivery_date)
    }
    # เพิ่มแผนงานในชีทที่ชื่อว่า 'Plan'
    plan_worksheet = sh.worksheet('title', 'Plan')
    plan_worksheet.append_table([plan_data['Job Name'], plan_data['Quantity'], plan_data['Delivery Date']])
    st.success("Plan uploaded successfully!")

# แสดงเครื่องจักรที่สามารถเลือกเพื่อ Assign งาน
selected_machine = st.selectbox("Select Machine", [machine['machines_name'] for machine in machines_data])

# การ Assign งานให้เครื่องจักร
if selected_machine:
    st.write(f"Assigning Job to {selected_machine}")

# การบันทึกเวลา Start และ End สำหรับการทำงาน
start_time = st.time_input("Start Time", datetime(2025, 6, 9, 8, 0))
end_time = st.time_input("End Time", datetime(2025, 6, 9, 16, 0))

# คำนวณระยะเวลา
if end_time > start_time:
    duration = (datetime.combine(datetime.today(), end_time) - datetime.combine(datetime.today(), start_time)).seconds / 3600
else:
    duration = 0

if st.button("Start Job"):
    st.write(f"Job started at {start_time}, duration: {duration} hours")

if st.button("End Job"):
    st.write(f"Job ended at {end_time}, duration: {duration} hours")

# แสดง % Utilization ของเครื่องจักร
total_available_time = 8  # เวลาเครื่องจักรสามารถทำงานได้ใน 1 วัน
assignments = [
    {'machine': selected_machine, 'job': job_name, 'start_time': start_time, 'end_time': end_time, 'duration': duration}
]
total_active_time = sum([assignment['duration'] for assignment in assignments])
utilization = (total_active_time / total_available_time) * 100
st.write(f"Machine Utilization: {utilization:.2f}%")
