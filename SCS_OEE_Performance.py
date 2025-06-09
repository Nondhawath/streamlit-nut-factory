import streamlit as st
import pandas as pd
from datetime import datetime

# ข้อมูลเครื่องจักร
machines = ['Machine 1', 'Machine 2', 'Machine 3']

# ข้อมูลงานที่ต้องทำ
jobs = ['Job A', 'Job B', 'Job C']

# บันทึกข้อมูลการ Assign งาน
assignments = []

# ฟังก์ชันในการคำนวณ % Utilization
def calculate_utilization(assignments, total_available_time):
    total_active_time = sum([assignment['duration'] for assignment in assignments])
    utilization = (total_active_time / total_available_time) * 100
    return utilization

# แสดง UI ใน Streamlit
st.title("Assign Job to Machines and Calculate Utilization")

# เลือกเครื่องจักร
selected_machine = st.selectbox("Select Machine", machines)

# เลือกงานที่ต้องการ Assign
selected_job = st.selectbox("Select Job", jobs)

# กำหนดเวลาเริ่มต้นและเวลาสิ้นสุด
start_time = st.time_input("Start Time", datetime(2025, 6, 9, 8, 0))
end_time = st.time_input("End Time", datetime(2025, 6, 9, 16, 0))

# คำนวณระยะเวลาในการทำงาน (เป็นชั่วโมง)
if end_time > start_time:
    duration = (datetime.combine(datetime.today(), end_time) - datetime.combine(datetime.today(), start_time)).seconds / 3600
else:
    duration = 0  # หากเวลาสิ้นสุดก่อนเวลาเริ่มต้น ให้ไม่คำนวณ

# เพิ่มข้อมูลการ Assign
if st.button("Assign Job"):
    assignments.append({
        'machine': selected_machine,
        'job': selected_job,
        'start_time': start_time,
        'end_time': end_time,
        'duration': duration
    })
    st.success(f"Assigned {selected_job} to {selected_machine} for {duration} hours")

# กำหนดเวลาเปิด-ปิดของเครื่องจักร
total_available_time = 8  # ตัวอย่าง 8 ชั่วโมงการทำงานใน 1 วัน

# คำนวณ % Utilization
utilization = calculate_utilization(assignments, total_available_time)

# แสดงข้อมูลการ Assign งานทั้งหมด
st.subheader("Assigned Jobs:")
df_assignments = pd.DataFrame(assignments)
st.write(df_assignments)

# แสดงผล % Utilization
st.subheader("Machine Utilization:")
st.write(f"{utilization:.2f}%")
