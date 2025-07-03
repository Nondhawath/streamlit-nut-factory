import streamlit as st
import psycopg2
import pandas as pd
import requests
import math
from datetime import datetime

# === Connection ===
def get_connection():
    return psycopg2.connect(st.secrets["postgres"]["conn_str"])

# === Telegram Notification ===
def send_telegram_message(message):
    token = st.secrets["telegram"]["token"]
    chat_id = st.secrets["telegram"]["chat_id"]
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}"
    try:
        requests.get(url)
    except Exception as e:
        st.error(f"Telegram แจ้งเตือนไม่สำเร็จ: {e}")

# === Database Operations ===
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

def get_jobs_by_status_list(status_list):
    with get_connection() as conn:
        qmarks = ','.join(['%s'] * len(status_list))
        sql = f"SELECT * FROM job_tracking WHERE status IN ({qmarks}) ORDER BY created_at DESC"
        return pd.read_sql(sql, conn, params=status_list)

def get_all_jobs():
    with get_connection() as conn:
        return pd.read_sql("SELECT * FROM job_tracking ORDER BY created_at DESC", conn)

# === Helper ===
def calculate_pieces(total_weight, barrel_weight, sample_weight, sample_count):
    if sample_count == 0:
        return 0
    try:
        return math.ceil((total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000))
    except ZeroDivisionError:
        return 0

# === Transfer Mode ===
def transfer_mode(dept_from):
    st.header(f"{dept_from} Transfer")
    df = get_jobs_by_status("TP Working")  # เลือกงานที่มีสถานะ TP Working

    if df.empty:
        st.warning("ไม่มีงานที่ต้องการส่งต่อ")
        return

    woc_list = df["woc_number"].tolist()
    woc_selected = st.selectbox("เลือก WOC ที่จะส่งต่อ", woc_list)
    job = df[df["woc_number"] == woc_selected].iloc[0]

    st.markdown(f"- **Part Name:** {job['part_name']}")
    st.markdown(f"- **Lot Number:** {job['lot_number']}")
    st.markdown(f"- **จำนวนชิ้นงาน:** {job['pieces_count']}")

    next_dept = st.selectbox("เลือกแผนกถัดไป", ["FI", "OS"])
    if st.button("ส่งต่อ"):
        update_status(woc_selected, f"{dept_from} Transfer {next_dept}")
        st.success(f"ส่ง WOC {woc_selected} ไปแผนก {next_dept}")
        send_telegram_message(f"{dept_from} ส่ง WOC {woc_selected} ไปแผนก {next_dept}")

# === Receive Mode ===
def receive_mode(dept_to):
    st.header(f"{dept_to} Receive")
    from_dept_map = {
        "TP": ["FM"],
        "FI": ["TP"],
        "OS": ["FM", "TP"]
    }
    from_depts = from_dept_map.get(dept_to, [])

    status_filters = [f"{fd} Transfer {dept_to}" for fd in from_depts]
    df = get_jobs_by_status_list(status_filters)

    if df.empty:
        st.warning("ไม่มีงานรอรับ")
        return

    woc_list = df["woc_number"].tolist()
    woc_selected = st.selectbox("เลือก WOC", woc_list)
    job = df[df["woc_number"] == woc_selected].iloc[0]

    st.markdown(f"- **Part Name:** {job['part_name']}")
    st.markdown(f"- **Lot Number:** {job['lot_number']}")
    st.markdown(f"- **จำนวนชิ้นงานเดิม:** {job['pieces_count']}")

    # บันทึกข้อมูลน้ำหนักใหม่
    total_weight = st.number_input("น้ำหนักรวม", min_value=0.0, step=0.01, value=0.0)
    barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0, step=0.01, value=0.0)
    sample_weight = st.number_input("น้ำหนักตัวอย่างรวม", min_value=0.0, step=0.01, value=0.0)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=0, step=1, value=0)

    pieces_new = calculate_pieces(total_weight, barrel_weight, sample_weight, sample_count)
    st.metric("จำนวนชิ้นงานที่คำนวณได้", pieces_new)

    # คำนวณ % คลาดเคลื่อน
    try:
        diff_pct = abs(pieces_new - job["pieces_count"]) / job["pieces_count"] * 100 if job["pieces_count"] > 0 else 0
    except Exception:
        diff_pct = 0
    st.metric("% คลาดเคลื่อน", f"{diff_pct:.2f}%")

    # แจ้งเตือน Telegram หากคลาดเคลื่อนเกิน 2%
    if diff_pct > 2:
        send_telegram_message(
            f"⚠️ ความคลาดเคลื่อนน้ำหนักเกิน 2% | แผนก: {dept_to} | WOC: {woc_selected} | Part: {job['part_name']} | "
            f"จำนวนเดิม: {job['pieces_count']} | จำนวนที่รับจริง: {pieces_new} | คลาดเคลื่อน: {diff_pct:.2f}%"
        )

    operator_name = st.text_input("ชื่อผู้ใช้งาน (Operator)")

    if st.button("รับเข้าและส่งต่อ"):
        next_status = f"WIP-{dept_to}"
        insert_job({
            "woc_number": woc_selected,
            "part_name": job["part_name"],
            "operator_name": operator_name,
            "dept_from": dept_to,
            "dept_to": "",  # ใส่แผนกต่อไปถ้ามีตาม flow
            "lot_number": job["lot_number"],
            "total_weight": total_weight,
            "barrel_weight": barrel_weight,
            "sample_weight": sample_weight,
            "sample_count": sample_count,
            "pieces_count": pieces_new,
            "status": next_status,
            "created_at": datetime.utcnow()
        })
        update_status(woc_selected, "TP Received")  # เปลี่ยนสถานะเป็น TP Received
        st.success("รับเข้าเรียบร้อยและบันทึกสถานะ")
        send_telegram_message(f"{dept_to} รับ WOC {woc_selected}")

# === Work Mode ===
def work_mode(dept):
    st.header(f"{dept} Work")
    # ดึงข้อมูลที่สถานะเป็น "TP Received" สำหรับแผนก Tapping
    df = get_jobs_by_status("TP Received")

    if df.empty:
        st.info("ไม่มีงานรอทำ")
        return

    woc_list = df["woc_number"].tolist()
    woc_selected = st.selectbox("เลือก WOC ที่จะทำงาน", woc_list)
    job = df[df["woc_number"] == woc_selected].iloc[0]

    st.markdown(f"- **Part Name:** {job['part_name']}")
    st.markdown(f"- **Lot Number:** {job['lot_number']}")
    st.markdown(f"- **จำนวน:** {job['pieces_count']}")

    machine_name = st.text_input("ชื่อเครื่องจักร")
    operator_name = st.text_input("ชื่อผู้ใช้งาน (Operator)")

    if st.button("เริ่มทำงาน"):
        if not machine_name.strip():
            st.error("กรุณากรอกชื่อเครื่องจักร")
            return
        update_status(woc_selected, "TP Working")  # เปลี่ยนสถานะเป็น TP Working
        st.success(f"เริ่มทำงาน WOC {woc_selected} ที่เครื่อง {machine_name}")
        send_telegram_message(f"{dept} เริ่มงาน WOC {woc_selected} ที่เครื่อง {machine_name} โดย {operator_name}")

# === Completion Mode ===
def completion_mode():
    st.header("Completion")
    # ดึงงานที่สถานะ Working ใน Final Inspection หรือ OS
    status_list = ["Used - FI01", "Used - FI30", "Used - FISM", "Used - OS01", "Used - OS30", "Used - OSSM"]
    df = get_jobs_by_status_list(status_list)
    if df.empty:
        st.info("ไม่มีงานรอ Completion")
        return

    woc_list = df["woc_number"].tolist()
    woc_selected = st.selectbox("เลือก WOC ที่จะทำ Completion", woc_list)

    ok = st.number_input("จำนวน OK", min_value=0, step=1)
    ng = st.number_input("จำนวน NG", min_value=0, step=1)
    rework = st.number_input("จำนวน Rework", min_value=0, step=1)
    remain = st.number_input("จำนวนคงเหลือ", min_value=0, step=1)

    operator_name = st.text_input("ชื่อผู้ใช้งาน (Operator)")

    if st.button("บันทึก Completion"):
        status = "Completed" if remain == 0 else "Remaining"
        update_status(woc_selected, status)
        st.success(f"บันทึก Completion เรียบร้อย สถานะอัปเดตเป็น {status}")
        send_telegram_message(
            f"📦 Completion WOC {woc_selected} | OK: {ok}, NG: {ng}, Rework: {rework}, Remain: {remain} โดย {operator_name}"
        )

# === Report Mode ===
def report_mode():
    st.header("รายงานและสรุป WIP")
    df = get_all_jobs()
    search = st.text_input("ค้นหา Part Name หรือ WOC")
    if search:
        df = df[df["part_name"].str.contains(search, case=False) | df["woc_number"].str.contains(search, case=False)]
    st.dataframe(df)

    st.markdown("### สรุป WIP แยกตามแผนก")
    depts = ["FM", "TP", "FI", "OS"]
    for d in depts:
        wip_df = df[df["status"].str.contains(f"WIP-{d}")]
        if wip_df.empty:
            st.write(f"แผนก {d}: ไม่มีงาน WIP")
        else:
            summary = wip_df.groupby("part_name").agg(
                จำนวนงาน=pd.NamedAgg(column="woc_number", aggfunc="count"),
                จำนวนชิ้นงาน=pd.NamedAgg(column="pieces_count", aggfunc="sum")
            ).reset_index()
            st.write(f"แผนก {d}")
            st.dataframe(summary)

# === Dashboard Mode ===
def dashboard_mode():
    st.header("Dashboard WIP รวม")
    df = get_all_jobs()
    depts = ["FM", "TP", "FI", "OS"]

    select_dept = st.selectbox("เลือกแผนก", ["ทั้งหมด"] + depts)

    if select_dept == "ทั้งหมด":
        filtered = df
    else:
        filtered = df[df["dept_to"] == select_dept]

    if filtered.empty:
        st.warning("ไม่มีข้อมูลสำหรับแผนกนี้")
        return

    grouped = filtered.groupby(["dept_to", "part_name"]).agg(
        จำนวนงาน=pd.NamedAgg(column="woc_number", aggfunc="count"),
        จำนวนชิ้นงาน=pd.NamedAgg(column="pieces_count", aggfunc="sum")
    ).reset_index()

    st.dataframe(grouped)

# === Main Function ===
def main():
    st.set_page_config(page_title="WOC Tracker", layout="wide")
    st.title("🏭 ระบบติดตามงานโรงงาน (Supabase + Streamlit)")

    menu = st.sidebar.selectbox("เลือกโหมด", [
        "Forming Transfer", "Tapping Transfer", "OS Transfer",
        "Tapping Receive", "Final Receive", "OS Receive",
        "Tapping Work", "Final Work",
        "Completion", "Report", "Dashboard"
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
    elif menu == "Report":
        report_mode()
    elif menu == "Dashboard":
        dashboard_mode()

if __name__ == "__main__":
    main()
