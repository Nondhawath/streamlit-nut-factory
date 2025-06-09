import streamlit as st
import pandas as pd
from datetime import datetime

# เพิ่มข้อความต้อนรับ
st.title("Manufacturing Job Assignment System")
st.markdown("Welcome to the job assignment system. Please input the job details, assign it to a machine, and track the utilization.")

# สร้างข้อมูลจำลองสำหรับเครื่องจักร
machines_data = pd.DataFrame({
    "machines_name": ["Machine A", "Machine B", "Machine C", "Machine D"],
    "status": ["Idle", "Running", "Idle", "Running"]
})

# แสดงข้อมูลเครื่องจักรในตารางที่ดูดี
st.subheader("Available Machines")
st.write("Below are the available machines:")
st.dataframe(machines_data.style.highlight_max(axis=0))  # Highlight max values for better UX

# ฟอร์มการอัปโหลดแผนงาน
st.subheader("Upload Job Plan")

# ให้ผู้ใช้กรอกข้อมูลแผนงาน
job_name = st.text_input("Job Name", placeholder="Enter the job name")
quantity = st.number_input("Quantity", min_value=1, step=1, placeholder="Enter the quantity")
delivery_date = st.date_input("Delivery Date", min_value=datetime.today())

# เพิ่มไอคอนและข้อความแนะนำ
st.markdown("### Job Information")
st.markdown("Fill in the job details and click `Upload Plan` to add it to the job list.")

# การอัปโหลดแผนงานไปยัง DataFrame
if st.button("Upload Plan"):
    plan_data = {
        'Job Name': job_name,
        'Quantity': quantity,
        'Delivery Date': str(delivery_date)
    }
    
    # สร้าง DataFrame จำลองสำหรับแผนงาน
    plan_df = pd.DataFrame([plan_data])

    # แสดงแผนงานในรูปแบบที่สวยงาม
    st.markdown("### Uploaded Plan")
    st.write(plan_df)
    st.success("Plan uploaded successfully!", icon="✅")

# เพิ่มการเลือกเครื่องจักรจากตาราง
st.subheader("Assign Job to Machine")
selected_machine = st.selectbox("Select Machine", machines_data['machines_name'])

# การแสดงข้อความเมื่อเลือกเครื่องจักร
if selected_machine:
    st.write(f"Job will be assigned to: **{selected_machine}**")
    st.markdown("### Set Start and End Time for the Job")

    # บันทึกเวลา Start และ End สำหรับการทำงาน
    start_time = st.time_input("Start Time", datetime(2025, 6, 9, 8, 0))
    end_time = st.time_input("End Time", datetime(2025, 6, 9, 16, 0))

    # คำนวณระยะเวลา
    if end_time > start_time:
        duration = (datetime.combine(datetime.today(), end_time) - datetime.combine(datetime.today(), start_time)).seconds / 3600
    else:
        duration = 0

    # เพิ่มปุ่ม Start และ End
    if st.button("Start Job"):
        st.write(f"Job started at {start_time}, duration: {duration} hours", icon="🕒")

    if st.button("End Job"):
        st.write(f"Job ended at {end_time}, duration: {duration} hours", icon="⏹️")

    # แสดง % Utilization ของเครื่องจักร
    total_available_time = 8  # เวลาเครื่องจักรสามารถทำงานได้ใน 1 วัน
    assignments = [
        {'machine': selected_machine, 'job': job_name, 'start_time': start_time, 'end_time': end_time, 'duration': duration}
    ]
    total_active_time = sum([assignment['duration'] for assignment in assignments])
    utilization = (total_active_time / total_available_time) * 100

    # แสดงผล % Utilization ด้วยกราฟ
    st.markdown("### Machine Utilization")
    st.progress(int(utilization))  # ใช้ progress bar แทนการแสดงเปอร์เซ็นต์ที่ง่าย

    st.write(f"Machine Utilization: {utilization:.2f}%")
