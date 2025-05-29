import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import os

st.set_page_config(page_title="Sorting Process App", layout="wide")

# ----------- Constants -----------
DATA_FILE = "sorting_report_full.xlsx"
EMP_FILE = "employee_master.xlsx"
PART_FILE = "part_master.xlsx"

# ----------- Load Master Data -----------
@st.cache_data
def load_master():
    if not os.path.exists(EMP_FILE):
        pd.DataFrame(columns=["ชื่อ", "ตำแหน่ง"]).to_excel(EMP_FILE, index=False)
    if not os.path.exists(PART_FILE):
        pd.DataFrame(columns=["รหัส", "ชื่อชิ้นงาน"]).to_excel(PART_FILE, index=False)
    return pd.read_excel(EMP_FILE), pd.read_excel(PART_FILE)

df_emp, df_part = load_master()
employees = df_emp['ชื่อ'].dropna().unique().tolist()
leaders = df_emp[df_emp['ตำแหน่ง'].str.contains("Leader", na=False)]['ชื่อ'].unique().tolist()
part_codes = df_part['รหัส'].dropna().unique().tolist()

# ----------- Load or Create Main Data -----------
def load_report():
    if os.path.exists(DATA_FILE):
        return pd.read_excel(DATA_FILE)
    else:
        columns = ["Timestamp", "Job ID", "Employee", "Part Code", "Total Checked", "NG", "Un-Tested", "Status", "Current Process", "Rework Time", "Leader", "Oil Cleaning Time", "Sender"]
        return pd.DataFrame(columns=columns)

report_df = load_report()

# ----------- Generate Job ID -----------
def generate_job_id(df):
    now = datetime.now()
    prefix = now.strftime("%y%m")
    if df.empty or "Job ID" not in df.columns:
        return f"{prefix}0001"
    latest = df[df["Job ID"].astype(str).str.startswith(prefix)]
    if latest.empty:
        return f"{prefix}0001"
    last_id = latest["Job ID"].max()
    next_id = int(last_id[-4:]) + 1
    return f"{prefix}{next_id:04d}"

# ----------- Select Process Mode -----------
mode = st.sidebar.selectbox("เลือกโหมดกระบวนการ", ["Sorting MC", "Waiting Judgement", "Oil Cleaning"])

if mode == "Sorting MC":
    st.header("🛠️ บันทึกข้อมูลจากกระบวนการ Sorting")
    with st.form("sorting_form"):
        col1, col2 = st.columns(2)
        with col1:
            employee = st.selectbox("ชื่อพนักงาน", employees)
            part_code = st.text_input("รหัสงาน (สามารถพิมพ์หรือเลือก)", "")
            dropdown = st.selectbox("เลือกรหัสงานจากรายการ", ["ไม่เลือก"] + part_codes)
            if dropdown != "ไม่เลือก":
                part_code = dropdown
            total_checked = st.number_input("จำนวนที่ตรวจ", min_value=0)
            ng = st.number_input("จำนวน NG", min_value=0)
            untested = st.number_input("จำนวนที่ตรวจไม่ทัน (Un-Tested)", min_value=0)

        with col2:
            status = st.selectbox("สถานะ", ["งาน NG จากเครื่อง"])
            current_process = "Sorting"

        submitted = st.form_submit_button("✅ บันทึกข้อมูล")
        if submitted:
            job_id = generate_job_id(report_df)
            new_row = {
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Job ID": job_id,
                "Employee": employee,
                "Part Code": part_code,
                "Total Checked": total_checked,
                "NG": ng,
                "Un-Tested": untested,
                "Status": status,
                "Current Process": current_process,
                "Rework Time": "",
                "Leader": "",
                "Oil Cleaning Time": "",
                "Sender": ""
            }
            report_df = pd.concat([report_df, pd.DataFrame([new_row])], ignore_index=True)
            report_df.to_excel(DATA_FILE, index=False)
            st.success(f"✅ บันทึกงานเรียบร้อย Job ID: {job_id}")

elif mode == "Waiting Judgement":
    st.header("🧑‍⚖️ งานรอการตัดสินใจ")
    wj_df = report_df[(report_df["Status"] == "งาน NG จากเครื่อง") & (report_df["Current Process"] == "Sorting")]
    for _, row in wj_df.iterrows():
        st.markdown(f"**Job ID:** {row['Job ID']} | รหัสงาน: {row['Part Code']} | จำนวน: {row['Total Checked']}")
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"Scrap - {row['Job ID']}"):
                report_df.loc[report_df['Job ID'] == row['Job ID'], 'Status'] = 'Scrap'
                report_df.to_excel(DATA_FILE, index=False)
                st.success(f"📛 งาน {row['Job ID']} ถูก Scrap แล้ว")
        with col2:
            if st.button(f"Rework - {row['Job ID']}"):
                leader = st.selectbox("เลือก Leader ตัดสินใจ", leaders, key=row['Job ID'])
                report_df.loc[report_df['Job ID'] == row['Job ID'], ['Status', 'Rework Time', 'Leader', 'Current Process']] = ['Rework', datetime.now().strftime("%Y-%m-%d %H:%M:%S"), leader, 'Oil Cleaning']
                report_df.to_excel(DATA_FILE, index=False)
                st.success(f"🔁 งาน {row['Job ID']} ถูกส่งไปล้าง")

elif mode == "Oil Cleaning":
    st.header("🧼 กระบวนการล้างงาน (Oil Cleaning)")
    oc_df = report_df[(report_df['Status'] == 'Rework') & (report_df['Current Process'] == 'Oil Cleaning')]
    for _, row in oc_df.iterrows():
        st.markdown(f"**Job ID:** {row['Job ID']} | รหัสงาน: {row['Part Code']} | สถานะ: {row['Status']}")
        if st.button(f"✅ ล้างเสร็จแล้ว - {row['Job ID']}"):
            report_df.loc[report_df['Job ID'] == row['Job ID'], ['Status', 'Oil Cleaning Time', 'Current Process']] = ['ล้างเสร็จแล้ว', datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'Sorting']
            report_df.to_excel(DATA_FILE, index=False)
            st.success(f"🧽 ล้างงาน {row['Job ID']} เสร็จแล้ว")

# ----------- WIP Display -----------
st.subheader("📦 WIP - งานที่อยู่ในกระบวนการ")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("### Sorting")
    st.dataframe(report_df[(report_df['Current Process'] == 'Sorting') & (~report_df['Status'].isin(['Scrap', 'ล้างเสร็จแล้ว']))][['Job ID', 'Part Code', 'Status']])
with col2:
    st.markdown("### Waiting Judgement")
    st.dataframe(report_df[(report_df['Status'] == 'งาน NG จากเครื่อง')][['Job ID', 'Part Code', 'Status']])
with col3:
    st.markdown("### Oil Cleaning")
    st.dataframe(report_df[(report_df['Current Process'] == 'Oil Cleaning') & (report_df['Status'] == 'Rework')][['Job ID', 'Part Code', 'Status']])

# ----------- Pie Chart -----------
st.subheader("📈 สัดส่วนสถานะงานทั้งหมด")
status_counts = report_df['Status'].value_counts()
fig, ax = plt.subplots()
ax.pie(status_counts, labels=status_counts.index, autopct='%1.1f%%', startangle=90)
ax.axis('equal')
st.pyplot(fig)

# ----------- Download -----------
st.download_button("📥 ดาวน์โหลดรายงานทั้งหมด", data=report_df.to_excel(index=False), file_name="sorting_report_full.xlsx")
