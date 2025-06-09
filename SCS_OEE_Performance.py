import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# สร้างข้อมูลงานจำลอง (มากกว่า 20 งาน) และจำนวนที่สุ่ม
job_names = [f"Job {i}" for i in range(1, 51)]  # สร้างชื่องานให้มากกว่า 50 งาน
quantities = np.random.randint(10000, 100000, size=len(job_names))  # สุ่มจำนวนหลักหมื่นถึงหลักแสน

# สร้าง DataFrame จำลองสำหรับงาน
jobs_data = pd.DataFrame({
    "Job Name": job_names,
    "Quantity": quantities,
    "Delivery Date": pd.date_range(start=datetime.today(), periods=len(job_names), freq='D')
})

# แสดงข้อมูล Dashboard
st.title("Manufacturing Job Dashboard")
st.markdown("Welcome to the Job Dashboard. Select a job to assign it to a machine and track utilization.")

# แสดงตารางงานที่มีข้อมูลจำลอง
st.subheader("Available Jobs")
st.write("Below are the available jobs with quantity and delivery date:")
st.dataframe(jobs_data.style.highlight_max(axis=0))  # ใช้ style เพื่อไฮไลท์ค่ามากที่สุดในแต่ละคอลัมน์

# ฟอร์มการเลือกงานจากตาราง
st.subheader("Assign Job to Machine")
selected_job = st.selectbox("Select Job", jobs_data['Job Name'])

# การแสดงข้อมูลของงานที่เลือก
if selected_job:
    job_details = jobs_data[jobs_data['Job Name'] == selected_job].iloc[0]
    st.write(f"**Job Name**: {job_details['Job Name']}")
    st.write(f"**Quantity**: {job_details['Quantity']}")
    st.write(f"**Delivery Date**: {job_details['Delivery Date']}")

    # เลือกเครื่องจักรที่จะแต่งตั้งงาน
    selected_machine = st.selectbox("Select Machine", ["Machine A", "Machine B", "Machine C", "Machine D"])

    # เลือกเวลาสำหรับการทำงาน
    st.markdown("### Set Start and End Time for the Job")
    start_time = st.time_input("Start Time", datetime(2025, 6, 9, 8, 0))
    end_time = st.time_input("End Time", datetime(2025, 6, 9, 16, 0))

    # คำนวณระยะเวลา
    if end_time > start_time:
        duration = (datetime.combine(datetime.today(), end_time) - datetime.combine(datetime.today(), start_time)).seconds / 3600
    else:
        duration = 0

    if st.button("Start Job"):
        st.write(f"Job started at {start_time}, duration: {duration} hours", icon="🕒")

    if st.button("End Job"):
        st.write(f"Job ended at {end_time}, duration: {duration} hours", icon="⏹️")

    # คำนวณ % Utilization ของเครื่องจักร
    total_available_time = 8  # เวลาเครื่องจักรสามารถทำงานได้ใน 1 วัน
    total_active_time = duration  # ระยะเวลาในการทำงานที่กำหนด
    utilization = (total_active_time / total_available_time) * 100

    # แสดงผล % Utilization ด้วยกราฟ
    st.markdown("### Machine Utilization")
    st.progress(int(utilization))  # ใช้ progress bar แทนการแสดงเปอร์เซ็นต์ที่ง่าย

    st.write(f"Machine Utilization: {utilization:.2f}%")

    # สร้างกราฟแสดงผลการทำงานของเครื่องจักร
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.pie([utilization, 100-utilization], labels=["Utilized", "Idle"], autopct='%1.1f%%', colors=["#4CAF50", "#FFC107"])
    ax.set_title(f"Utilization of {selected_machine}")
    st.pyplot(fig)
