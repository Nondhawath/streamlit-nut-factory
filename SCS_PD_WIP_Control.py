import streamlit as st
import psycopg2
import pandas as pd
import requests
from datetime import datetime

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

# ====== HELPER ======
def calculate_pieces(total_weight, barrel_weight, sample_weight, sample_count):
    return (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)

# ====== MODE 1: FORMING TRANSFER ======
def mode_forming_transfer():
    st.header("Forming Transfer")
    dept_from = st.selectbox("แผนกต้นทาง", ["FM"])
    dept_to = st.selectbox("แผนกปลายทาง", ["TP", "FI", "OS"])
    woc = st.text_input("WOC Number")
    part_name = st.text_input("Part Name")
    lot = st.text_input("Lot Number")
    total = st.number_input("น้ำหนักรวม", 0.0)
    barrel = st.number_input("น้ำหนักถัง", 0.0)
    sample_w = st.number_input("น้ำหนักตัวอย่างรวม", 0.0)
    sample_c = st.number_input("จำนวนตัวอย่าง", 1)

    if total and barrel and sample_w and sample_c:
        pieces = calculate_pieces(total, barrel, sample_w, sample_c)
        st.metric("จำนวนชิ้นงาน", f"{pieces:.2f}")

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
        st.success("บันทึกเรียบร้อย")
        send_telegram_message(f"{dept_from} ส่ง WOC {woc} ไปยัง {dept_to}")

# ====== MODE 2: TAPPING RECEIVE ======
def mode_tp_receive():
    st.header("Tapping Receive")
    df = get_jobs_by_status("FM Transfer TP")
    if df.empty:
        st.warning("ไม่มีงานจาก FM ที่ส่งมา TP")
        return

    woc = st.selectbox("เลือก WOC ที่จะรับ", df["woc_number"].tolist())
    selected = df[df["woc_number"] == woc].iloc[0]

    if st.button("ตรวจสอบน้ำหนัก"):
        total = st.number_input("น้ำหนักรวม", 0.0)
        barrel = st.number_input("น้ำหนักถัง", 0.0)
        sample_w = st.number_input("น้ำหนักตัวอย่างรวม", 0.0)
        sample_c = st.number_input("จำนวนตัวอย่าง", 1)
        if total and barrel and sample_w and sample_c:
            pieces_new = calculate_pieces(total, barrel, sample_w, sample_c)
            diff_percent = abs((pieces_new - selected["pieces_count"]) / selected["pieces_count"]) * 100
            st.metric("% ต่างกัน", f"{diff_percent:.2f}%")
            if st.button("บันทึกรับงาน"):
                insert_job({
                    "woc_number": selected["woc_number"],
                    "part_name": selected["part_name"],
                    "operator_name": "นายคมสันต์",
                    "dept_from": "FM",
                    "dept_to": "TP",
                    "lot_number": selected["lot_number"],
                    "total_weight": total,
                    "barrel_weight": barrel,
                    "sample_weight": sample_w,
                    "sample_count": sample_c,
                    "pieces_count": pieces_new,
                    "status": "WIP-TP"
                })
                update_status(woc, "TP Received")
                send_telegram_message(f"TP รับ WOC {woc}")

# ====== MODE 3: TAPPING WORK ======
def mode_tp_work():
    st.header("Tapping Work")
    df = get_jobs_by_status("WIP-TP")
    if df.empty:
        st.info("ไม่มีงานที่รอทำ")
        return
    woc = st.selectbox("เลือก WOC", df["woc_number"])
    machine = st.selectbox("เลือกเครื่อง", ["TP30", "TP40"])
    if st.button("บันทึกงานที่เครื่อง"):
        update_status(woc, f"Used - {machine}")
        send_telegram_message(f"TP ใช้งาน WOC {woc} ที่ {machine}")

# ====== MODE 4: TP TRANSFER ======
def mode_tp_transfer():
    st.header("TP Transfer")
    parent_woc = st.selectbox("WOC เดิมที่ต้องการโอน", [row["woc_number"] for row in get_jobs_by_status("Used - TP30").to_dict('records')])
    woc_new = st.text_input("WOC ใหม่")
    dept_to = st.selectbox("แผนกปลายทาง", ["FI", "OS"])
    part_name = st.text_input("Part Name")
    lot = st.text_input("Lot Number")
    total = st.number_input("น้ำหนักรวม", 0.0)
    barrel = st.number_input("น้ำหนักถัง", 0.0)
    sample_w = st.number_input("น้ำหนักตัวอย่างรวม", 0.0)
    sample_c = st.number_input("จำนวนตัวอย่าง", 1)

    if st.button("โอนและสร้าง WOC ใหม่"):
        pieces = calculate_pieces(total, barrel, sample_w, sample_c)
        insert_job({
            "woc_number": woc_new,
            "parent_woc": parent_woc,
            "part_name": part_name,
            "operator_name": "นายคมสันต์",
            "dept_from": "TP",
            "dept_to": dept_to,
            "lot_number": lot,
            "total_weight": total,
            "barrel_weight": barrel,
            "sample_weight": sample_w,
            "sample_count": sample_c,
            "pieces_count": pieces,
            "status": f"TP Transfer {dept_to}"
        })
        update_status(parent_woc, "Completed")
        st.success("โอนและสร้าง WOC ใหม่เรียบร้อย")

# ====== MAIN ======
def main():
    st.set_page_config(page_title="WOC Job Tracker", layout="wide")
    st.title("📦 ระบบโอนถ่ายงานโรงงาน")
    menu = st.sidebar.radio("เลือกโหมด", [
        "Forming Transfer", "Tapping Receive", "Tapping Work", "TP Transfer"
    ])

    if menu == "Forming Transfer":
        mode_forming_transfer()
    elif menu == "Tapping Receive":
        mode_tp_receive()
    elif menu == "Tapping Work":
        mode_tp_work()
    elif menu == "TP Transfer":
        mode_tp_transfer()

if __name__ == "__main__":
    main()
