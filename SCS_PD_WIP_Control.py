import streamlit as st
import psycopg2
import pandas as pd
import requests
from datetime import datetime
import math

# ====== DATABASE CONNECTION ======
def get_connection():
    return psycopg2.connect(st.secrets["postgres"]["conn_str"])

# ====== TELEGRAM ======
def send_telegram_message(message):
    token = st.secrets["telegram"]["token"]
    chat_id = st.secrets["telegram"]["chat_id"]
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}"
    requests.get(url)

# ====== DATABASE OPERATIONS ======
def insert_job(data: dict):
    conn = get_connection()
    cur = conn.cursor()
    columns = ', '.join(data.keys())
    placeholders = ', '.join(['%s'] * len(data))
    sql = f"INSERT INTO job_tracking ({columns}) VALUES ({placeholders})"
    cur.execute(sql, list(data.values()))
    conn.commit()
    cur.close()
    conn.close()

def update_status(woc_number, new_status):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE job_tracking SET status = %s WHERE woc_number = %s", (new_status, woc_number))
    conn.commit()
    cur.close()
    conn.close()

def get_jobs_by_status(status):
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM job_tracking WHERE status = %s ORDER BY created_at DESC", conn, params=(status,))
    conn.close()
    return df

def get_all_jobs():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM job_tracking ORDER BY created_at DESC", conn)
    conn.close()
    return df

# ====== HELPER ======
def calculate_pieces(total_weight, barrel_weight, sample_weight, sample_count):
    return math.ceil((total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000))

# ====== MODE FUNCTIONS ======
def mode_transfer(dept_from):
    st.header(f"{dept_from} Transfer")
    prev_woc = st.text_input("WOC ก่อนหน้า (ถ้ามี)") if dept_from != "FM" else ""
    dept_to = st.selectbox("แผนกปลายทาง", ["TP", "FI", "OS"])
    woc = st.text_input("WOC ใหม่")
    part_name = st.text_input("Part Name")
    lot = st.text_input("Lot Number")
    total = st.number_input("น้ำหนักรวม", 0.0)
    barrel = st.number_input("น้ำหนักถัง", 0.0)
    sample_w = st.number_input("น้ำหนักตัวอย่างรวม", 0.0)
    sample_c = st.number_input("จำนวนตัวอย่าง", min_value=1)

    if total and barrel and sample_w and sample_c:
        pieces = calculate_pieces(total, barrel, sample_w, sample_c)
        st.metric("จำนวนชิ้นงาน (ปัดขึ้น)", f"{pieces:,}")

    if st.button("บันทึก"):
        status = f"{dept_from} Transfer {dept_to}"
        insert_job({
            "woc_number": woc,
            "part_name": part_name,
            "operator_name": "นายคมสันต์",
            "dept_from": dept_from,
            "dept_to": dept_to,
            "lot_number": lot,
            "total_weight": total,
            "barrel_weight": barrel,
            "sample_weight": sample_w,
            "sample_count": sample_c,
            "pieces_count": pieces,
            "status": status
        })
        if prev_woc:
            update_status(prev_woc, "Completed")
        st.success("บันทึกเรียบร้อยแล้ว")
        send_telegram_message(f"{dept_from} ส่ง WOC {woc} ไปยัง {dept_to}")


def mode_receive(dept_to):
    st.header(f"{dept_to} Receive")
    from_status = f"FM Transfer {dept_to}" if dept_to == "TP" else f"TP Transfer {dept_to}"
    df = get_jobs_by_status(from_status)
    if df.empty:
        st.warning("ไม่มีงานที่รอรับ")
        return
    woc = st.selectbox("เลือก WOC", df["woc_number"])
    selected = df[df["woc_number"] == woc].iloc[0]

    total = st.number_input("น้ำหนักรวม", 0.0)
    barrel = st.number_input("น้ำหนักถัง", 0.0)
    sample_w = st.number_input("น้ำหนักรวมของตัวอย่าง", 0.0)
    sample_c = st.number_input("จำนวนตัวอย่าง", min_value=1)

    if total and barrel and sample_w and sample_c:
        pieces_new = calculate_pieces(total, barrel, sample_w, sample_c)
        diff_percent = abs((pieces_new - selected["pieces_count"]) / selected["pieces_count"]) * 100
        st.metric("% ต่างกัน", f"{diff_percent:.2f}%")

        if diff_percent > 2:
            send_telegram_message(f"⚠️ ความคลาดเคลื่อนน้ำหนักเกิน 2% | WOC: {woc} | Part: {selected['part_name']} | Operator: นายคมสันต์ | คลาดเคลื่อน: {diff_percent:.2f}%")

        if st.button("รับงาน"):
            insert_job({
                "woc_number": selected["woc_number"],
                "part_name": selected["part_name"],
                "operator_name": "นายคมสันต์",
                "dept_from": dept_to,
                "dept_to": f"{dept_to}-On_MC",
                "lot_number": selected["lot_number"],
                "total_weight": total,
                "barrel_weight": barrel,
                "sample_weight": sample_w,
                "sample_count": sample_c,
                "pieces_count": pieces_new,
                "status": f"WIP-{dept_to}"
            })
            update_status(woc, f"{dept_to} Received")
            st.success(f"รับงาน {woc} เรียบร้อยแล้ว")
            send_telegram_message(f"{dept_to} รับ WOC {woc}")


def mode_work(dept):
    st.header(f"{dept} Work")
    df = get_jobs_by_status(f"WIP-{dept}")
    if df.empty:
        st.info("ไม่มีงานรอทำ")
        return
    woc = st.selectbox("เลือก WOC", df["woc_number"])
    selected = df[df["woc_number"] == woc].iloc[0]
    st.write("Part:", selected["part_name"])
    st.write("Lot:", selected["lot_number"])
    st.write("จำนวน:", selected["pieces_count"])
    machine = st.selectbox("เลือกเครื่อง", [f"{dept}01", f"{dept}30", f"{dept}SM"])
    if st.button("เริ่มงาน"):
        update_status(woc, f"Used - {machine}")
        st.success(f"บันทึกงาน WOC {woc} แล้ว")
        send_telegram_message(f"{dept} เริ่มงาน WOC {woc} ที่เครื่อง {machine}")


def mode_completion():
    st.header("Completion")
    df = get_jobs_by_status("Used - FI01")
    if df.empty:
        st.warning("ไม่มีงานที่รอ Completion")
        return
    woc = st.selectbox("เลือก WOC", df["woc_number"])
    ok = st.number_input("จำนวน OK", 0)
    ng = st.number_input("จำนวน NG", 0)
    rework = st.number_input("จำนวน Rework", 0)
    remain = st.number_input("จำนวนคงเหลือ", 0)
    if st.button("บันทึก Completion"):
        status = "Completed" if remain == 0 else "Remaining"
        update_status(woc, status)
        st.success(f"สถานะ WOC {woc} อัพเดตเป็น {status}")
        send_telegram_message(f"📦 Completion: {woc} | OK: {ok} | NG: {ng} | Rework: {rework} | Remain: {remain}")


def mode_export():
    st.header("Export Job Data")
    df = get_all_jobs()
    search = st.text_input("ค้นหา WOC หรือ Part Name")
    if search:
        df = df[df["woc_number"].str.contains(search) | df["part_name"].str.contains(search)]
    st.dataframe(df)
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 ดาวน์โหลด Excel (CSV)", data=csv, file_name="job_tracking_export.csv")


def mode_report():
    st.header("📊 Dashboard รายงาน")
    df = get_all_jobs()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("ทั้งหมด", len(df))
    with col2:
        st.metric("เสร็จสิ้นแล้ว", len(df[df["status"] == "Completed"]))
    st.bar_chart(df["status"].value_counts())
    st.dataframe(df)


# ====== MAIN ======
def main():
    st.set_page_config(page_title="WOC Job Tracker", layout="wide")
    st.title("📦 ระบบโอนถ่ายงานโรงงาน")
    menu = st.sidebar.selectbox("เลือกโหมด", [
        "Forming Transfer", "Tapping Transfer", "OS Transfer",
        "Tapping Receive", "Final Receive", "OS Receive",
        "Tapping Work", "Final Work",
        "Completion", "Export", "Report"
    ])

    if menu == "Forming Transfer":
        mode_transfer("FM")
    elif menu == "Tapping Transfer":
        mode_transfer("TP")
    elif menu == "OS Transfer":
        mode_transfer("OS")
    elif menu == "Tapping Receive":
        mode_receive("TP")
    elif menu == "Final Receive":
        mode_receive("FI")
    elif menu == "OS Receive":
        mode_receive("OS")
    elif menu == "Tapping Work":
        mode_work("TP")
    elif menu == "Final Work":
        mode_work("FI")
    elif menu == "Completion":
        mode_completion()
    elif menu == "Export":
        mode_export()
    elif menu == "Report":
        mode_report()

if __name__ == "__main__":
    main()
