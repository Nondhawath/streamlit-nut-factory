import streamlit as st
import pandas as pd
import random

# สร้างฟังก์ชันสำหรับอัปโหลดแผนงาน
def upload_plan():
    st.header("อัปโหลดแผนการผลิต")
    
    uploaded_file = st.file_uploader("เลือกไฟล์ CSV หรือ Excel เพื่ออัปโหลดแผนการผลิต", type=["csv", "xlsx"])
    if uploaded_file is not None:
        # อ่านข้อมูลจากไฟล์ที่อัปโหลด
        if uploaded_file.type == "application/vnd.ms-excel" or uploaded_file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            plan_df = pd.read_excel(uploaded_file)
        else:
            plan_df = pd.read_csv(uploaded_file)
        
        # แสดงข้อมูลแผนงานที่อัปโหลด
        st.write(plan_df)
        
        return plan_df
    return None

# ฟังก์ชันคำนวณเวลาในการผลิต
def calculate_production_time(plan_df, capacity=300):
    plan_df["เวลาผลิต (นาที)"] = plan_df["จำนวน"] / capacity
    return plan_df

# ฟังก์ชันการ Assign งานให้เครื่องจักร
def assign_jobs(plan_df):
    st.header("Assign งานให้เครื่องจักร")
    
    machine_list = ["Machine A", "Machine B", "Machine C", "Machine D"]
    assigned_machine = st.selectbox("เลือกเครื่องจักรที่ต้องการ Assign งาน", machine_list)
    
    plan_df["เครื่องจักรที่ Assign"] = assigned_machine
    
    # แสดงข้อมูลหลังจาก Assign งาน
    st.write(plan_df)
    
    return plan_df

# ฟังก์ชันการบันทึกผลการผลิต
def record_production_results(plan_df):
    st.header("บันทึกผลการผลิต")
    
    for index, row in plan_df.iterrows():
        st.write(f"ผลการผลิตสำหรับ P/No: {row['P/No']}")
        ok_count = st.number_input(f"จำนวน OK สำหรับ P/No {row['P/No']}", min_value=0, max_value=row["จำนวน"], value=0, key=f"ok_{index}")
        ng_count = st.number_input(f"จำนวน NG สำหรับ P/No {row['P/No']}", min_value=0, max_value=row["จำนวน"], value=0, key=f"ng_{index}")
        
        # การคำนวณ UnTest
        untest_count = row["จำนวน"] - (ok_count + ng_count)
        st.write(f"จำนวนที่ยังไม่ทดสอบ: {untest_count}")
        
        plan_df.at[index, "จำนวน OK"] = ok_count
        plan_df.at[index, "จำนวน NG"] = ng_count
        plan_df.at[index, "จำนวนยังไม่ทดสอบ"] = untest_count
    
    # แสดงข้อมูลหลังจากบันทึกผล
    st.write(plan_df)

# ส่วนการแสดงผลใน Streamlit
def main():
    st.title("ระบบการจัดการแผนการผลิตและการ Assign งาน")

    # อัปโหลดแผนงาน
    plan_df = upload_plan()
    
    if plan_df is not None:
        # คำนวณเวลาในการผลิต
        plan_df = calculate_production_time(plan_df)
        
        # แสดงข้อมูลแผนงานและเวลาผลิต
        st.write("ข้อมูลแผนการผลิตพร้อมเวลาในการผลิต")
        st.write(plan_df)
        
        # Assign งานให้เครื่องจักร
        plan_df = assign_jobs(plan_df)
        
        # บันทึกผลการผลิต
        record_production_results(plan_df)
        
if __name__ == "__main__":
    main()
