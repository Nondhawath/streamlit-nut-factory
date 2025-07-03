import streamlit as st
import psycopg2
import pandas as pd
import requests
import math

# ====== CONNECTION ======
def get_connection():
    return psycopg2.connect(st.secrets["postgres"]["conn_str"])

# ====== TELEGRAM ======
def send_telegram_message(message):
    token = st.secrets["telegram"]["token"]
    chat_id = st.secrets["telegram"]["chat_id"]
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}"
    try:
        requests.get(url)
    except Exception as e:
        st.error("Telegram แจ้งเตือนไม่สำเร็จ: " + str(e))

# ====== DATABASE ======
def insert_job(data):
    with get_connection() as conn:
        cur = conn.cursor()
        keys = ', '.join(data.keys())
        values = ', '.join(['%s'] * len(data))
        sql = f"INSERT INTO job_tracking ({keys}) VALUES ({values})"
        cur.execute(sql, list(data.values()))
        conn.commit()

def update_status(woc, new_status):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE job_tracking SET status = %s WHERE woc_number = %s", (new_status, woc))
        conn.commit()

def get_jobs_by_status(status):
    with get_connection() as conn:
        return pd.read_sql("SELECT * FROM job_tracking WHERE status = %s ORDER BY created_at DESC", conn, params=(status,))

def get_all_jobs():
    with get_connection() as conn:
        return pd.read_sql("SELECT * FROM job_tracking ORDER BY created_at DESC", conn)

def get_jobs_by_multiple_status(status_list):
    with get_connection() as conn:
        qmarks = ','.join(['%s'] * len(status_list))
        sql = f"SELECT * FROM job_tracking WHERE status IN ({qmarks}) ORDER BY created_at DESC"
        return pd.read_sql(sql, conn, params=status_list)

# ====== HELPER ======
def calculate_pieces(total, barrel, sample_weight, sample_count):
    if sample_count == 0:
        return 0
    try:
        return math.ceil((total - barrel) / ((sample_weight / sample_count) / 1000))
    except ZeroDivisionError:
        return 0

# ====== RECEIVE MODE ======
def receive_mode(dept_to):
    st.subheader(f"{dept_to} Receive")
    from_dept_map = {
        "TP": ["FM"],
        "FI": ["TP"],
        "OS": ["FM", "TP"]
    }
    from_depts = from_dept_map.get(dept_to, ["FM"])
    status_filters = [f"{fd} Transfer {dept_to}" for fd in from_depts]

    df = get_jobs_by_multiple_status(status_filters)
    if df.empty:
        st.warning("ไม่มีงานที่รอรับ")
        return

    search = st.text_input("ค้นหา WOC หรือ Part Name")
    if search:
        df = df[df["woc_number"].str.contains(search, case=False) | df["part_name"].str.contains(search, case=False)]

    woc = st.selectbox("เลือก WOC", df["woc_number"])
    job = df[df["woc_number"] == woc].iloc[0]
    st.write(f"Part: {job['part_name']}, Lot: {job['lot_number']}, จำนวนเดิม: {job['pieces_count']}")

    total = st.number_input("น้ำหนักรวม", min_value=0.0, step=0.01, value=job["total_weight"])
    barrel = st.number_input("น้ำหนักถัง", min_value=0.0, step=0.01, value=job["barrel_weight"])
    sample_weight = st.number_input("น้ำหนักตัวอย่างรวม", min_value=0.0, step=0.01, value=job["sample_weight"])
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=0, step=1, value=job["sample_count"])

    pieces_new = calculate_pieces(total, barrel, sample_weight, sample_count)
    st.metric("จำนวนชิ้นงานที่คำนวณได้", f"{pieces_new:,}")

    if job["pieces_count"] == 0:
        diff_pct = 0.0
    else:
        diff_pct = abs(pieces_new - job["pieces_count"]) / job["pieces_count"] * 100
    st.metric("% คลาดเคลื่อน", f"{diff_pct:.2f}%")

    if diff_pct > 2:
        send_telegram_message(
            f"⚠️ ความคลาดเคลื่อนน้ำหนักเกิน 2% | แผนก: {dept_to} | WOC: {woc} | Part: {job['part_name']} | "
            f"จำนวนเดิม: {job['pieces_count']} | จำนวนที่รับจริง: {pieces_new} | คลาดเคลื่อน: {diff_pct:.2f}%"
        )

    if st.button("รับเข้าและส่งต่อ"):
        insert_job({
            "woc_number": woc,
            "part_name": job["part_name"],
            "operator_name": "นายคมสันต์",
            "dept_from": dept_to,
            "dept_to": f"{dept_to}-On_MC",
            "lot_number": job["lot_number"],
            "total_weight": total,
            "barrel_weight": barrel,
            "sample_weight": sample_weight,
            "sample_count": sample_count,
            "pieces_count": pieces_new,
            "status": f"WIP-{dept_to}"
        })
        update_status(woc, f"{dept_to} Received")
        send_telegram_message(f"{dept_to} รับ WOC {woc}")
        st.success("รับเข้าเรียบร้อย")

# ====== DASHBOARD ======
def dashboard_mode():
    st.subheader("📊 Dashboard ภาพรวม")
    df = get_all_jobs()
    dept_filter = st.selectbox("เลือกแผนก", ["ทั้งหมด", "FM", "TP", "FI", "OS"])
    if dept_filter != "ทั้งหมด":
        df = df[df["dept_to"].str.contains(dept_filter)]

    if df.empty:
        st.warning("ไม่มีข้อมูล")
        return

    summary = df[df["status"].str.contains("WIP")].groupby("dept_to").agg(
        จำนวนงาน=pd.NamedAgg(column="woc_number", aggfunc="count"),
        จำนวนชิ้นงาน=pd.NamedAgg(column="pieces_count", aggfunc="sum")
    ).reset_index()
    st.dataframe(summary)

    st.markdown("### รายการ WIP รายละเอียด")
    st.dataframe(df[df["status"].str.contains("WIP")][["woc_number", "part_name", "dept_to", "pieces_count"]])

# ====== PLACEHOLDER FOR OTHER MODES ======
def transfer_mode(dept_from):
    st.info(f"ยังไม่ได้กำหนดโหมด {dept_from} Transfer")

def work_mode(dept):
    st.info(f"ยังไม่ได้กำหนดโหมด {dept} Work")

def completion_mode():
    st.info("ยังไม่ได้กำหนดโหมด Completion")

def export_mode():
    st.info("ยังไม่ได้กำหนดโหมด Export")

def report_mode():
    st.info("ยังไม่ได้กำหนดโหมด Report")

# ====== MAIN ======
def main():
    st.set_page_config("WOC Tracker", layout="wide")
    st.title("🏭 ระบบติดตามงานโรงงาน (Supabase)")

    menu = st.sidebar.selectbox("เลือกโหมด", [
        "Forming Transfer", "Tapping Transfer", "OS Transfer",
        "Tapping Receive", "Final Receive", "OS Receive",
        "Tapping Work", "Final Work",
        "Completion", "Export", "Report", "Dashboard"
    ])

    if menu == "Forming Transfer":
        transfer_mode("FM")
    elif menu == "Tapping Transfer":
        transfer_mode("TP")
    elif menu == "OS Transfer":
        transfer_mode("OS")
    elif menu == "Tapping Receive":
        receive_mode("TP")
    elif menu == "Final Receive":
        receive_mode("FI")
    elif menu == "OS Receive":
        receive_mode("OS")
    elif menu == "Tapping Work":
        work_mode("TP")
    elif menu == "Final Work":
        work_mode("FI")
    elif menu == "Completion":
        completion_mode()
    elif menu == "Export":
        export_mode()
    elif menu == "Report":
        report_mode()
    elif menu == "Dashboard":
        dashboard_mode()

if __name__ == "__main__":
    main()
