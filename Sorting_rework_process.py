import streamlit as st
import pandas as pd
import datetime
import os
import uuid
import matplotlib.pyplot as plt

# ========== CONFIGURATION ==========
DATA_FILE = "sorting_data.csv"

# ========== LOAD EXCEL MASTER DATA ==========
@st.cache_data
def load_employee_data():
    df = pd.read_excel("รายชื่อพนักงานแผนก Final Inspection.xlsx")
    return df['รายชื่อ'].dropna().tolist(), df[df['ตำแหน่ง'] == 'Leader']['รายชื่อ'].dropna().tolist()

@st.cache_data
def load_job_codes():
    df = pd.read_excel("Master list SCS part name.xlsx")
    return df['Part Code'].dropna().tolist()

# ========== INITIALIZE MASTER DATA ==========
employees, leaders = load_employee_data()
job_codes = load_job_codes()

# ========== CREATE OR LOAD CSV ==========
if not os.path.exists(DATA_FILE):
    df_empty = pd.DataFrame(columns=[
        "timestamp", "employee", "job_code", "inspected_qty", "ng_qty", "untest_qty",
        "status", "sent_to", "sent_by", "sent_time"
    ])
    df_empty.to_csv(DATA_FILE, index=False)

def load_data():
    return pd.read_csv(DATA_FILE)

def save_data(new_row):
    df = load_data()
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)

# ========== UI ==========
st.title("Sorting Rework Process")

st.header("📝 กรอกข้อมูลการตรวจสอบ")
with st.form("sorting_form"):
    employee = st.selectbox("ชื่อพนักงานผู้ตรวจสอบ", employees)

    job_code = st.text_input("รหัสงาน (สามารถพิมพ์หรือเลือกจากรายการ)")
    job_code_dropdown = st.selectbox("เลือกจากรายการรหัสงาน", ["ไม่เลือก"] + job_codes)
    if job_code_dropdown != "ไม่เลือก":
        job_code = job_code_dropdown

    inspected_qty = st.number_input("จำนวนที่ตรวจ", min_value=0, step=1)
    ng_qty = st.number_input("จำนวน NG", min_value=0, step=1)
    untest_qty = st.number_input("จำนวนที่ยังไม่ตรวจ (Un test)", min_value=0, step=1)
    status = st.selectbox("สถานะงาน", ["Rework", "Scrap"])

    submitted = st.form_submit_button("บันทึกข้อมูล")
    if submitted:
        new_row = {
            "timestamp": datetime.datetime.now().isoformat(),
            "employee": employee,
            "job_code": job_code,
            "inspected_qty": inspected_qty,
            "ng_qty": ng_qty,
            "untest_qty": untest_qty,
            "status": status,
            "sent_to": "",
            "sent_by": "",
            "sent_time": ""
        }
        save_data(new_row)
        st.success("✅ บันทึกข้อมูลเรียบร้อยแล้ว")

# ========== TRANSFER SECTION ==========
st.header("📦 การส่งงานระหว่างแผนก")
data = load_data()

for idx, row in data[data['status'] == 'Rework'].iterrows():
    if row['sent_to'] == "":
        st.subheader(f"🔄 งานรหัส {row['job_code']} จาก {row['employee']}")
        if st.button(f"ส่งไปแผนก Oil Cleaning - งาน {row['job_code']}", key=f"send_oil_{idx}"):
            leader = st.selectbox("เลือกชื่อ Leader", leaders, key=f"leader_{idx}")
            data.at[idx, 'sent_to'] = "Oil Cleaning"
            data.at[idx, 'sent_by'] = leader
            data.at[idx, 'sent_time'] = datetime.datetime.now().isoformat()
            data.to_csv(DATA_FILE, index=False)
            st.success(f"✅ ส่งงานไปยังแผนก Oil Cleaning โดย {leader}")

    elif row['sent_to'] == "Oil Cleaning":
        st.subheader(f"🔁 งานรหัส {row['job_code']} อยู่ที่ Oil Cleaning")
        if st.button(f"ส่งกลับแผนก Sorting - งาน {row['job_code']}", key=f"return_sorting_{idx}"):
            sender = st.selectbox("เลือกชื่อพนักงานที่ส่งกลับ", employees, key=f"return_emp_{idx}")
            data.at[idx, 'sent_to'] = "Sorting"
            data.at[idx, 'sent_by'] = sender
            data.at[idx, 'sent_time'] = datetime.datetime.now().isoformat()
            data.to_csv(DATA_FILE, index=False)
            st.success(f"✅ ส่งกลับไป Sorting โดย {sender}")

# ========== REPORT ==========
st.header("📊 รายงานข้อมูล")
selected_status = st.selectbox("กรองตามสถานะ", ["ทั้งหมด", "Rework", "Scrap"])
data['timestamp'] = pd.to_datetime(data['timestamp'])
selected_date = st.date_input("เลือกวันที่", datetime.date.today())

filtered = data[data['timestamp'].dt.date == selected_date]
if selected_status != "ทั้งหมด":
    filtered = filtered[filtered['status'] == selected_status]

st.dataframe(filtered)

# ========== PIE CHART ==========
st.subheader("📈 สัดส่วน Scrap กับ Rework")
count = data['status'].value_counts()
fig, ax = plt.subplots()
ax.pie(count, labels=count.index, autopct='%1.1f%%', startangle=90)
ax.axis('equal')
st.pyplot(fig)
