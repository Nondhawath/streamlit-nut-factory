import streamlit as st
import pandas as pd
import random

# ฟังก์ชันสำหรับอัปโหลดแผนงาน
def upload_plan():
    st.header("อัปโหลดแผนการผลิต")
    
    uploaded_file = st.file_uploader("เลือกไฟล์ CSV หรือ Excel เพื่ออัปโหลดแผนการผลิต", type=["csv", "xlsx"])
    
    if uploaded_file is not None:
        # อ่านข้อมูลจากไฟล์ที่อัปโหลด
        if uploaded_file.type == "application/vnd.ms-excel" or uploaded_file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            plan_df = pd.read_excel(uploaded_file)
        else:
            plan_df = pd.read_csv(uploaded_file)
        
        st.write("ข้อมูลแผนงานที่อัปโหลด:")
        st.write(plan_df)
        
        # ตรวจสอบชื่อคอลัมน์
        if "P/No" not in plan_df.columns or "จำนวน" not in plan_df.columns:
            st.error("ไฟล์ที่อัปโหลดไม่มีคอลัมน์ 'P/No' หรือ 'จำนวน' กรุณาตรวจสอบและลองใหม่")
            return None
        
        # ตรวจสอบข้อมูลซ้ำ (ใช้ P/No และ จำนวนเป็นเงื่อนไข)
        if "plan_df" in st.session_state:
            existing_plans = st.session_state.plan_df
            new_plans = plan_df[~plan_df[['P/No', 'จำนวน']].apply(tuple, 1).isin(existing_plans[['P/No', 'จำนวน']].apply(tuple, 1))]
            if not new_plans.empty:
                # ถ้ามีข้อมูลใหม่ให้เพิ่มลงใน session_state
                st.session_state.plan_df = pd.concat([existing_plans, new_plans], ignore_index=True)
                st.success(f"แผนการผลิตที่ไม่ซ้ำถูกเพิ่มแล้ว {len(new_plans)} รายการ")
            else:
                st.warning("ไม่มีแผนการผลิตใหม่ที่ไม่ซ้ำ!")
        else:
            st.session_state.plan_df = plan_df
            st.success(f"แผนการผลิตถูกเพิ่มแล้ว {len(plan_df)} รายการ")
        
        return st.session_state.plan_df
    
    return None

# ฟังก์ชันคำนวณเวลาในการผลิต
def calculate_production_time(plan_df, capacity=300):
    plan_df["เวลาผลิต (นาที)"] = plan_df["จำนวน"] / capacity
    return plan_df

# ฟังก์ชันการ Assign งานให้เครื่องจักร
def assign_jobs(plan_df):
    st.header("Assign งานให้เครื่องจักร")
    
    # ข้อมูลเครื่องจักร
    machines = ["Machine A", "Machine B", "Machine C", "Machine D"]
    
    # คำนวณเวลาในการผลิต
    capacity_per_machine = 480  # เครื่องจักร 1 เครื่องมีความสามารถ 480 นาที (100%)
    machine_capacity = {machine: capacity_per_machine for machine in machines}
    
    assignments = []  # เก็บการ Assign งาน
    
    for index, row in plan_df.iterrows():
        job_name = row["P/No"]
        required_time = row["เวลาผลิต (นาที)"] * 60  # คำนวณเวลาในหน่วยนาที
        
        st.write(f"Job: {job_name}, จำนวน: {row['จำนวน']}, เวลาในการผลิต: {required_time:.2f} นาที")
        
        # Dropdown เลือกเครื่องจักร
        selected_machine = st.selectbox(f"เลือกเครื่องจักรสำหรับงาน {job_name}", machines, key=f"select_{index}")
        
        # คำนวณว่าเครื่องจักรสามารถทำงานนี้ได้หรือไม่
        remaining_capacity = machine_capacity[selected_machine]
        
        if remaining_capacity >= required_time:
            st.write(f"เครื่องจักร {selected_machine} สามารถทำงานนี้ได้ภายในเวลา {required_time:.2f} นาที")
            machine_capacity[selected_machine] -= required_time  # ลดเวลาใช้งานเครื่องจักร
            assignments.append({"P/No": job_name, "เครื่องจักร": selected_machine, "เวลาที่ใช้": required_time})
        else:
            st.write(f"เครื่องจักร {selected_machine} ไม่สามารถทำงานนี้ได้เนื่องจากเวลาไม่พอ (จำเป็นต้องใช้เวลา {required_time:.2f} นาที)")
    
    # ปุ่มยืนยันการ Assign
    if st.button("ยืนยันการ Assign"):
        if assignments:
            st.success("การ Assign งานสำเร็จ!")
            st.write(assignments)
        else:
            st.warning("ยังไม่มีการ Assign งานใดๆ")

    return plan_df

# ฟังก์ชันการบันทึกผลการผลิต
def record_production_results(plan_df):
    st.header("บันทึกผลการผลิต")
    
    # เลือกเครื่องจักรจาก Dropdown
    machine_list = ["Machine A", "Machine B", "Machine C", "Machine D"]
    selected_machine = st.selectbox("เลือกเครื่องจักรที่ต้องการบันทึกผลการผลิต", machine_list)
    
    # กรองแสดง Job ที่ถูก Assign ให้เครื่องจักรที่เลือก
    assigned_jobs = plan_df[plan_df["เครื่องจักรที่ Assign"] == selected_machine]
    
    # ถ้ามีการ Assign งานแล้วให้แสดงรายการ
    if not assigned_jobs.empty:
        for index, row in assigned_jobs.iterrows():
            st.write(f"Job: {row['P/No']}, จำนวน: {row['จำนวน']}, เครื่องจักร: {row['เครื่องจักรที่ Assign']}")
            ok_count = st.number_input(f"จำนวน OK สำหรับ P/No {row['P/No']}", min_value=0, max_value=row["จำนวน"], value=0, key=f"ok_{index}")
            ng_count = st.number_input(f"จำนวน NG สำหรับ P/No {row['P/No']}", min_value=0, max_value=row["จำนวน"], value=0, key=f"ng_{index}")
            
            untest_count = row["จำนวน"] - (ok_count + ng_count)
            st.write(f"จำนวนที่ยังไม่ทดสอบ: {untest_count}")
            
            # เพิ่มปุ่มยืนยันการเสร็จสิ้น
            if st.button(f"ยืนยันการเสร็จสิ้นสำหรับ P/No {row['P/No']}", key=f"finish_{index}"):
                st.success(f"บันทึกผลการผลิตสำหรับ P/No {row['P/No']} เสร็จสมบูรณ์")
                plan_df.at[index, "จำนวน OK"] = ok_count
                plan_df.at[index, "จำนวน NG"] = ng_count
                plan_df.at[index, "จำนวนยังไม่ทดสอบ"] = untest_count
    
    else:
        st.warning("ยังไม่มีงานที่ถูก Assign ให้เครื่องจักรนี้")

    st.write(plan_df)

# ฟังก์ชันการแสดงรายงาน
def generate_report(plan_df):
    st.header("รายงานการผลิต")
    st.write("รายงานการเปรียบเทียบแผนการผลิตและผลการผลิตจริง:")
    st.write(plan_df)

# โหมดหลัก
def main():
    st.title("ระบบการจัดการแผนการผลิตและการ Assign งาน")
    
    mode = st.sidebar.selectbox("เลือกโหมด", ["อัปโหลดแผนการผลิต", "Assign งาน", "คำนวณเวลาและบันทึกผลการผลิต", "รายงาน"])
    
    if mode == "อัปโหลดแผนการผลิต":
        plan_df = upload_plan()
        if plan_df is not None:
            plan_df = calculate_production_time(plan_df)
            st.write("ข้อมูลแผนการผลิตพร้อมเวลาในการผลิต")
            st.write(plan_df)
    
    elif mode == "Assign งาน":
        if 'plan_df' not in st.session_state:
            st.warning("กรุณาอัปโหลดแผนการผลิตก่อน")
        else:
            plan_df = assign_jobs(st.session_state.plan_df)
    
    elif mode == "คำนวณเวลาและบันทึกผลการผลิต":
        if 'plan_df' not in st.session_state:
            st.warning("กรุณาอัปโหลดแผนการผลิตก่อน")
        else:
            record_production_results(st.session_state.plan_df)
    
    elif mode == "รายงาน":
        if 'plan_df' not in st.session_state:
            st.warning("กรุณาอัปโหลดแผนการผลิตก่อน")
        else:
            generate_report(st.session_state.plan_df)

if __name__ == "__main__":
    main()
