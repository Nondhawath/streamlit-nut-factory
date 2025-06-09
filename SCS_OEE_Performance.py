import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# สร้างข้อมูลจำลองสำหรับเครื่องจักร
machines_data = pd.DataFrame({
    "Machine Name": [f"Machine {i}" for i in range(1, 6)],
    "Status": ["Idle", "Running", "Idle", "Running", "Maintenance"],
    "Current Job": ["Job 1", "Job 2", "Job 3", "Job 4", "Job 5"],
    "Job Progress": [75, 60, 100, 40, 20]  # เปอร์เซ็นต์การทำงาน
})

# สร้าง Dashboard
st.title("Manufacturing Job Dashboard")
st.markdown("### Overview of all Machines")

# แสดงเครื่องจักรทั้งหมดในตาราง
st.dataframe(machines_data)

# เพิ่มไอคอนให้คลิกเพื่อดูรายละเอียดงานของเครื่องจักร
for i, row in machines_data.iterrows():
    machine_name = row['Machine Name']
    status = row['Status']
    current_job = row['Current Job']
    job_progress = row['Job Progress']

    # ใช้ st.markdown สำหรับการแสดงไอคอนที่สามารถคลิกได้
    if st.button(f"🔧 {machine_name} - {status}", key=machine_name):
        st.subheader(f"Details for {machine_name}")
        st.write(f"**Status**: {status}")
        st.write(f"**Current Job**: {current_job}")
        st.write(f"**Job Progress**: {job_progress}%")
        st.write("### Set Start and End Time for the Job")
        
        # ฟอร์มการตั้งเวลาเริ่มต้นและสิ้นสุดสำหรับการทำงาน
        start_time = st.time_input(f"Start Time for {machine_name}", datetime(2025, 6, 9, 8, 0))
        end_time = st.time_input(f"End Time for {machine_name}", datetime(2025, 6, 9, 16, 0))

        # คำนวณระยะเวลา
        if end_time > start_time:
            duration = (datetime.combine(datetime.today(), end_time) - datetime.combine(datetime.today(), start_time)).seconds / 3600
        else:
            duration = 0

        st.write(f"**Duration**: {duration} hours")
        st.progress(job_progress)  # แสดงเปอร์เซ็นต์ความคืบหน้า
        st.write(f"Job Progress for {machine_name}: {job_progress}%")
        st.write(f"Machine Utilization: {duration / 8 * 100:.2f}%")
