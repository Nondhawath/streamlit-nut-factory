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

# สร้างข้อมูลจำลองสำหรับงานที่อัปโหลด
job_names = [f"Job {i}" for i in range(1, 6)]
quantities = np.random.randint(10000, 100000, size=len(job_names))

jobs_data = pd.DataFrame({
    "Job Name": job_names,
    "Quantity": quantities,
    "Delivery Date": pd.date_range(start=datetime.today(), periods=len(job_names), freq='D')
})

# Sidebar สำหรับเลือกโหมดต่าง ๆ
mode = st.sidebar.radio("Select Mode", ("Monitoring", "Assign", "Upload Plan", "User"))

if mode == "Monitoring":
    st.title("Monitoring Mode")
    st.markdown("### Overview of All Machines")
    st.dataframe(machines_data)

    # เพิ่มไอคอนให้คลิกเพื่อดูรายละเอียดงานของเครื่องจักร
    for i, row in machines_data.iterrows():
        machine_name = row['Machine Name']
        status = row['Status']
        current_job = row['Current Job']
        job_progress = row['Job Progress']

        if st.button(f"🔧 {machine_name} - {status}", key=machine_name):
            st.subheader(f"Details for {machine_name}")
            st.write(f"**Status**: {status}")
            st.write(f"**Current Job**: {current_job}")
            st.write(f"**Job Progress**: {job_progress}%")
            st.write("### Set Start and End Time for the Job")
            
            start_time = st.time_input(f"Start Time for {machine_name}", datetime(2025, 6, 9, 8, 0))
            end_time = st.time_input(f"End Time for {machine_name}", datetime(2025, 6, 9, 16, 0))

            # คำนวณระยะเวลา
            if end_time > start_time:
                duration = (datetime.combine(datetime.today(), end_time) - datetime.combine(datetime.today(), start_time)).seconds / 3600
            else:
                duration = 0

            st.write(f"**Duration**: {duration} hours")
            st.progress(job_progress)
            st.write(f"Job Progress for {machine_name}: {job_progress}%")
            st.write(f"Machine Utilization: {duration / 8 * 100:.2f}%")

elif mode == "Assign":
    st.title("Assign Job to Machine")
    st.markdown("### Select Job and Machine to Assign")
    
    selected_job = st.selectbox("Select Job", jobs_data['Job Name'])
    selected_machine = st.selectbox("Select Machine", machines_data['Machine Name'])

    # แสดงรายละเอียดงานที่เลือก
    if selected_job:
        job_details = jobs_data[jobs_data['Job Name'] == selected_job].iloc[0]
        st.write(f"**Job Name**: {job_details['Job Name']}")
        st.write(f"**Quantity**: {job_details['Quantity']}")
        st.write(f"**Delivery Date**: {job_details['Delivery Date']}")

    # การมอบหมายงานให้กับเครื่องจักร
    if st.button("Assign Job"):
        st.write(f"Assigned **{selected_job}** to **{selected_machine}**")

elif mode == "Upload Plan":
    st.title("Upload Job Plan")
    st.markdown("### Upload New Plan")
    
    job_name = st.text_input("Job Name", placeholder="Enter the job name")
    quantity = st.number_input("Quantity", min_value=1, step=1, placeholder="Enter the quantity")
    delivery_date = st.date_input("Delivery Date", min_value=datetime.today())
    
    if st.button("Upload Plan"):
        plan_data = {
            'Job Name': job_name,
            'Quantity': quantity,
            'Delivery Date': str(delivery_date)
        }
        # เพิ่มแผนงานลงใน DataFrame
        new_plan_df = pd.DataFrame([plan_data])
        jobs_data = pd.concat([jobs_data, new_plan_df], ignore_index=True)
        st.success(f"Job Plan '{job_name}' uploaded successfully!")
        st.write(jobs_data)

elif mode == "User":
    st.title("User Mode")
    st.markdown("### See Your Daily Jobs")

    # แสดงรายการงานที่กำลังดำเนินการ
    current_jobs = jobs_data.sample(3)  # ใช้ sample สำหรับจำลองข้อมูล 3 งานที่กำลังทำ
    st.write("**Current Jobs for Today**:")
    st.dataframe(current_jobs)

    # เลือกงานที่ต้องการทำ
    selected_user_job = st.selectbox("Select Job to Start", current_jobs['Job Name'])

    if selected_user_job:
        st.write(f"**Selected Job**: {selected_user_job}")
        start_time = st.time_input("Start Time", datetime(2025, 6, 9, 8, 0))
        end_time = st.time_input("End Time", datetime(2025, 6, 9, 16, 0))

        if st.button("Start Job"):
            st.write(f"Started {selected_user_job} at {start_time}")
        
        if st.button("Finish Job"):
            st.write(f"Finished {selected_user_job} at {end_time}")
            # คำนวณระยะเวลา
            duration = (datetime.combine(datetime.today(), end_time) - datetime.combine(datetime.today(), start_time)).seconds / 3600
            st.write(f"**Job Duration**: {duration} hours")
