import streamlit as st
import pandas as pd
import datetime
import os
from io import BytesIO

st.set_page_config(page_title="Nut Factory Sorting", layout="wide")
st.title("📦 ระบบติดตามงานคัดแยกน๊อต (Sorting Tracking System)")

# ---------- Session State Initial ----------
if "employee_df" not in st.session_state:
    emp_path = "/mnt/data/รายชื่อพนักงานแผนก Final Inspection.xlsx"
    st.session_state.employee_df = pd.read_excel(emp_path)

if "part_df" not in st.session_state:
    part_path = "/mnt/data/Master list SCS part name.xlsx"
    st.session_state.part_df = pd.read_excel(part_path)

if "report_df" not in st.session_state:
    st.session_state.report_df = pd.DataFrame()

# ---------- Load Employee & Part Code ----------
employees = st.session_state.employee_df.iloc[:, 0].dropna().unique().tolist()
part_codes = st.session_state.part_df.iloc[:, 0].dropna().unique().tolist()

# ---------- Generate Job ID ----------
def generate_job_id():
    now = datetime.datetime.now()
    prefix = now.strftime("%y%m")
    report_df = st.session_state.report_df
    if not report_df.empty and "Job ID" in report_df.columns:
        filtered = report_df[report_df["Job ID"].astype(str).str.startswith(prefix)]
        count = len(filtered) + 1
    else:
        count = 1
    return f"{prefix}{count:04d}"

# ---------- Submit Section ----------
st.sidebar.header("เลือกโหมดกระบวนการ")
mode = st.sidebar.radio("โหมดงาน", ["Sorting MC", "Waiting Judgement", "Oil Cleaning"])

with st.form("sorting_form"):
    if mode == "Sorting MC":
        st.subheader("📝 บันทึกงาน Sorting")
        job_id = generate_job_id()
        part_code = st.selectbox("เลือกรหัสงาน", options=part_codes)
        employee = st.selectbox("ชื่อพนักงาน", options=employees)
        quantity_checked = st.number_input("จำนวนที่ตรวจ", min_value=0)
        quantity_ng = st.number_input("จำนวน NG", min_value=0)
        quantity_remaining = st.number_input("จำนวนที่ยังไม่ตรวจ", min_value=0)
        submit = st.form_submit_button("✅ บันทึกงาน")

        if submit:
            st.success(f"บันทึกสำเร็จ Job ID: {job_id}")
            new_row = {
                "วันที่": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Job ID": job_id,
                "รหัสงาน": part_code,
                "พนักงาน": employee,
                "ตรวจแล้ว": quantity_checked,
                "NG": quantity_ng,
                "ยังไม่ตรวจ": quantity_remaining,
                "สถานะ": "Sorting MC"
            }
            st.session_state.report_df = pd.concat([st.session_state.report_df, pd.DataFrame([new_row])], ignore_index=True)

    elif mode == "Waiting Judgement":
        st.subheader("⚖️ ตัดสินใจ Scrap / Rework")
        df = st.session_state.report_df
        waiting_df = df[df["สถานะ"] == "Sorting MC"]
        selected = st.selectbox("เลือกรายการที่ต้องตัดสินใจ", options=waiting_df["Job ID"].tolist())
        judge_name = st.selectbox("ชื่อผู้พิจารณา", options=employees)
        col1, col2 = st.columns(2)
        if col1.form_submit_button("🗑️ Scrap"):
            st.session_state.report_df.loc[df["Job ID"] == selected, ["สถานะ", "ผู้พิจารณา"]] = ["Scrap", judge_name]
            st.success(f"บันทึกสถานะ Scrap สำหรับ Job ID: {selected}")
        if col2.form_submit_button("🔁 Rework"):
            st.session_state.report_df.loc[df["Job ID"] == selected, ["สถานะ", "ผู้พิจารณา"]] = ["Oil Cleaning", judge_name]
            st.success(f"ส่งต่อไปล้างน้ำมัน Job ID: {selected}")

    elif mode == "Oil Cleaning":
        st.subheader("🧼 ล้างน้ำมันเสร็จ")
        df = st.session_state.report_df
        cleaning_df = df[df["สถานะ"] == "Oil Cleaning"]
        selected = st.selectbox("เลือกรายการที่ล้างน้ำมันเสร็จ", options=cleaning_df["Job ID"].tolist())
        if st.form_submit_button("✅ ล้างเสร็จแล้ว"):
            st.session_state.report_df.loc[df["Job ID"] == selected, "สถานะ"] = "Lavage"
            st.success(f"อัปเดตสถานะล้างเสร็จแล้วสำหรับ Job ID: {selected}")

# ---------- WIP Dashboard ----------
st.markdown("---")
st.header("📊 งานคงค้างแต่ละสถานะ (WIP)")
df = st.session_state.report_df
if not df.empty:
    wip_status = df[df["สถานะ"].isin(["Sorting MC", "Oil Cleaning"])]
    st.dataframe(wip_status, use_container_width=True)

    # Pie chart
    pie_df = df["สถานะ"].value_counts().reset_index()
    pie_df.columns = ["สถานะ", "จำนวน"]
    st.plotly_chart({
        "data": [{
            "type": "pie",
            "labels": pie_df["สถานะ"],
            "values": pie_df["จำนวน"]
        }],
        "layout": {"title": "สัดส่วนสถานะทั้งหมด"}
    })

    # Download
    output = BytesIO()
    df.to_excel(output, index=False)
    st.download_button("📥 ดาวน์โหลดรายงาน Excel", data=output.getvalue(), file_name="sorting_report_updated.xlsx")
else:
    st.info("ยังไม่มีข้อมูลบันทึก")
