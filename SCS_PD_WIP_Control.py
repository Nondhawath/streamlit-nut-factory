# 📦 WOC Job Tracking System with Supabase + Streamlit
import streamlit as st
import psycopg2
import pandas as pd
import requests
from datetime import datetime
import math

# ====== CONNECTION ======
def get_connection():
    return psycopg2.connect(st.secrets["postgres"]["conn_str"])

# ====== TELEGRAM ======
def send_telegram_message(message):
    token = st.secrets["telegram"]["token"]
    chat_id = st.secrets["telegram"]["chat_id"]
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}"
    requests.get(url)

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


# ====== HELPER ======
def calculate_pieces(total, barrel, sample_weight, sample_count):
    return math.ceil((total - barrel) / ((sample_weight / sample_count) / 1000))


# ====== MODES ======
def transfer_mode(dept_from):
    st.subheader(f"{dept_from} Transfer")
    prev_woc = st.selectbox("WOC ก่อนหน้า", get_all_jobs()["woc_number"].unique()) if dept_from != "FM" else ""
    new_woc = st.text_input("WOC ใหม่")
    part_name = ""

    if prev_woc:
        df = get_all_jobs()
        part_name = df[df["woc_number"] == prev_woc]["part_name"].values[0]
        st.text_input("Part Name", value=part_name, disabled=True)
    else:
        part_name = st.text_input("Part Name")

    dept_to = st.selectbox("แผนกปลายทาง", ["TP", "FI", "OS"])
    lot = st.text_input("Lot Number")
    total = st.number_input("น้ำหนักรวม", 0.0)
    barrel = st.number_input("น้ำหนักถัง", 0.0)
    sample_weight = st.number_input("น้ำหนักตัวอย่างรวม", 0.0)
    sample_count = st.number_input("จำนวนตัวอย่าง", 1)

    if all([total, barrel, sample_weight, sample_count]):
        pieces = calculate_pieces(total, barrel, sample_weight, sample_count)
        st.metric("จำนวนชิ้นงาน", pieces)

    if st.button("บันทึก Transfer"):
        insert_job({
            "woc_number": new_woc,
            "part_name": part_name,
            "operator_name": "นายคมสันต์",
            "dept_from": dept_from,
            "dept_to": dept_to,
            "lot_number": lot,
            "total_weight": total,
            "barrel_weight": barrel,
            "sample_weight": sample_weight,
            "sample_count": sample_count,
            "pieces_count": pieces,
            "status": f"{dept_from} Transfer {dept_to}"
        })
        if prev_woc:
            update_status(prev_woc, "Completed")
        send_telegram_message(f"{dept_from} ส่ง WOC {new_woc} ไป {dept_to}")
        st.success("บันทึกเรียบร้อย")


def receive_mode(dept_to):
    st.subheader(f"{dept_to} Receive")
    from_dept = "FM" if dept_to == "TP" else "TP" if dept_to == "FI" else "FI"
    df = get_jobs_by_status(f"{from_dept} Transfer {dept_to}")
    if df.empty:
        st.warning("ไม่มีงานที่รอรับ")
        return

    woc = st.selectbox("เลือก WOC", df["woc_number"])
    job = df[df["woc_number"] == woc].iloc[0]
    st.write(f"Part: {job['part_name']}, Lot: {job['lot_number']}, จำนวนเดิม: {job['pieces_count']}")

    total = st.number_input("น้ำหนักรวม", 0.0)
    barrel = st.number_input("น้ำหนักถัง", 0.0)
    sample_weight = st.number_input("น้ำหนักตัวอย่างรวม", 0.0)
    sample_count = st.number_input("จำนวนตัวอย่าง", 1)

    if all([total, barrel, sample_weight, sample_count]):
        new_pieces = calculate_pieces(total, barrel, sample_weight, sample_count)
        diff = abs(new_pieces - job["pieces_count"])
        diff_pct = (diff / job["pieces_count"]) * 100
        st.metric("% คลาดเคลื่อน", f"{diff_pct:.2f}%")

        if diff_pct > 2:
            send_telegram_message(f"⚠️ คลาดเคลื่อน >2% | WOC: {woc} | Part: {job['part_name']} | คลาดเคลื่อน: {diff_pct:.2f}% | ให้หัวหน้าตรวจสอบ")

        if st.button("รับเข้าและส่งต่อ Tapping Work"):
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
                "pieces_count": new_pieces,
                "status": f"WIP-{dept_to}"
            })
            update_status(woc, f"{dept_to} Received")
            send_telegram_message(f"{dept_to} รับงาน {woc}")
            st.success("รับเข้าเรียบร้อย")


def work_mode(dept):
    st.subheader(f"{dept} Work")
    df = get_jobs_by_status(f"WIP-{dept}")
    if df.empty:
        st.warning("ไม่มีงานรอทำ")
        return

    woc = st.selectbox("เลือก WOC", df["woc_number"])
    job = df[df["woc_number"] == woc].iloc[0]
    st.write(f"Part: {job['part_name']}, Lot: {job['lot_number']}, จำนวน: {job['pieces_count']}")
    machine = st.selectbox("เลือกเครื่อง", [f"{dept}01", f"{dept}30", f"{dept}SM"])

    if st.button("เริ่มทำงาน"):
        update_status(woc, f"Used - {machine}")
        send_telegram_message(f"{dept} เริ่มงาน WOC {woc} ที่เครื่อง {machine}")
        st.success("บันทึกเริ่มงานเรียบร้อย")


def completion_mode():
    st.subheader("Completion")
    df = get_all_jobs()
    df = df[df["status"].str.startswith("Used")]
    if df.empty:
        st.info("ไม่มีงานรอ Completion")
        return

    woc = st.selectbox("เลือก WOC", df["woc_number"])
    ok = st.number_input("จำนวน OK", 0)
    ng = st.number_input("จำนวน NG", 0)
    rw = st.number_input("จำนวน Rework", 0)
    remain = st.number_input("คงเหลือ", 0)

    if st.button("บันทึก Completion"):
        status = "Completed" if remain == 0 else "Remaining"
        update_status(woc, status)
        send_telegram_message(f"📦 Completion WOC {woc} | OK:{ok}, NG:{ng}, Rework:{rw}, Remain:{remain}")
        st.success(f"สถานะอัปเดตเป็น {status}")


def export_mode():
    df = get_all_jobs()
    st.download_button("📥 Export CSV", df.to_csv(index=False).encode("utf-8-sig"), "job_tracking.csv")
    st.dataframe(df)


def report_mode():
    df = get_all_jobs()
    st.metric("ทั้งหมด", len(df))
    st.metric("เสร็จแล้ว", len(df[df.status == "Completed"]))
    st.bar_chart(df["status"].value_counts())
    st.dataframe(df)


# ====== MAIN ======
def main():
    st.set_page_config("WOC Tracker", layout="wide")
    st.title("🏭 ระบบติดตามงานโรงงาน (Supabase)")
    menu = st.sidebar.selectbox("เลือกโหมด", [
        "Forming Transfer", "Tapping Transfer", "OS Transfer",
        "Tapping Receive", "Final Receive", "OS Receive",
        "Tapping Work", "Final Work",
        "Completion", "Export", "Report"])

    if menu == "Forming Transfer": transfer_mode("FM")
    elif menu == "Tapping Transfer": transfer_mode("TP")
    elif menu == "OS Transfer": transfer_mode("OS")
    elif menu == "Tapping Receive": receive_mode("TP")
    elif menu == "Final Receive": receive_mode("FI")
    elif menu == "OS Receive": receive_mode("OS")
    elif menu == "Tapping Work": work_mode("TP")
    elif menu == "Final Work": work_mode("FI")
    elif menu == "Completion": completion_mode()
    elif menu == "Export": export_mode()
    elif menu == "Report": report_mode()

if __name__ == "__main__":
    main()
