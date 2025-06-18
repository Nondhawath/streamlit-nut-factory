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
    
    machine_list = ["Machine A", "Machine B", "Machine C", "Machine D"]
    assigned_machine = st.selectbox("เลือกเครื่องจักรที่ต้องการ Assign งาน", machine_list)
    
    plan_df["เครื่องจักรที่ Assign"] = assigned_machine
    
    st.write(plan_df)
    
    return plan_df

# ฟังก์ชันการบันทึกผลการผลิต
def record_production_results(plan_df):
    st.header("บันทึกผลการผลิต")
    
    for index, row in plan_df.iterrows():
        st.write(f"ผลการผลิตสำหรับ P/No: {row['P/No']}")
        ok_count = st.number_input(f"จำนวน OK สำหรับ P/No {row['P/No']}", min_value=0, max_value=row["จำนวน"], value=0, key=f"ok_{index}")
        ng_count = st.number_input(f"จำนวน NG สำหรับ P/No {row['P/No']}", min_value=0, max_value=row["จำนวน"], value=0, key=f"ng_{index}")
        
        untest_count = row["จำนวน"] - (ok_count + ng_count)
        st.write(f"จำนวนที่ยังไม่ทดสอบ: {untest_count}")
        
        plan_df.at[index, "จำนวน OK"] = ok_count
        plan_df.at[index, "จำนวน NG"] = ng_count
        plan_df.at[index, "จำนวนยังไม่ทดสอบ"] = untest_count
    
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
