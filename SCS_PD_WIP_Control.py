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

# ====== MODES ======
def transfer_mode(dept_from):
    st.subheader(f"{dept_from} Transfer")
    operator_name = st.text_input("ชื่อผู้ปฏิบัติงาน (Operator)")
    
    if dept_from == "FM":
        prev_woc = None
    else:
        all_jobs = get_all_jobs()
        prev_woc_options = [""] + list(all_jobs[all_jobs["status"].str.contains(f"{dept_from}-Working")]["woc_number"].unique())
        prev_woc = st.selectbox("WOC ก่อนหน้า (ถ้ามี)", prev_woc_options)

    new_woc = st.text_input("WOC ใหม่")
    part_name = ""
    if prev_woc:
        all_jobs = get_all_jobs()
        filtered = all_jobs[all_jobs["woc_number"] == prev_woc]
        if not filtered.empty:
            part_name = filtered["part_name"].values[0]
        st.text_input("Part Name", value=part_name, disabled=True)
    else:
        part_name = st.text_input("Part Name")

    dept_to = st.selectbox("แผนกปลายทาง", ["TP", "FI", "OS"])
    lot = st.text_input("Lot Number")
    total = st.number_input("น้ำหนักรวม", min_value=0.0, step=0.01)
    barrel = st.number_input("น้ำหนักถัง", min_value=0.0, step=0.01)
    sample_weight = st.number_input("น้ำหนักตัวอย่างรวม", min_value=0.0, step=0.01)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=0, step=1, value=0)

    pieces = 0
    if all([total > 0, barrel >= 0, sample_weight > 0, sample_count > 0]):
        pieces = calculate_pieces(total, barrel, sample_weight, sample_count)
        st.metric("จำนวนชิ้นงาน (คำนวณ)", pieces)

    if st.button("บันทึก Transfer"):
        if not operator_name.strip():
            st.error("กรุณากรอกชื่อผู้ปฏิบัติงาน")
            return
        if not new_woc.strip():
            st.error("กรุณากรอก WOC ใหม่")
            return
        if pieces == 0:
            st.error("กรุณากรอกข้อมูลน้ำหนักและจำนวนตัวอย่างให้ถูกต้อง")
            return

        insert_job({
            "woc_number": new_woc,
            "part_name": part_name,
            "operator_name": operator_name,
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
        st.success(f"บันทึกการส่งงาน WOC {new_woc} สำเร็จ")
        send_telegram_message(f"{dept_from} ส่ง WOC {new_woc} ไป {dept_to} โดย {operator_name}")

def receive_mode(dept_to):
    st.subheader(f"{dept_to} Receive")
    operator_name = st.text_input("ชื่อผู้ปฏิบัติงาน (Operator)")
    
    # แผนกต้นทางที่รับได้
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

    st.write(f"Part Name: {job['part_name']}")
    st.write(f"Lot Number: {job['lot_number']}")
    st.write(f"จำนวนชิ้นงานก่อนหน้า: {job['pieces_count']}")

    # เลือกแผนกถัดไป และสถานะเปลี่ยนเป็น WIP-แผนกนั้น
    next_dept_map = {
        "TP": "TP-On_MC",
        "FI": "FI-On_MC",
        "OS": "OS-On_MC"
    }
    next_status = next_dept_map.get(dept_to, f"WIP-{dept_to}")
    next_dept = st.selectbox("แผนกถัดไป", [next_status])

    # กรอกข้อมูลน้ำหนักใหม่เพื่อบันทึก
    total = st.number_input("น้ำหนักรวม", min_value=0.0, step=0.01, value=0.0)
    barrel = st.number_input("น้ำหนักถัง", min_value=0.0, step=0.01, value=0.0)
    sample_weight = st.number_input("น้ำหนักตัวอย่างรวม", min_value=0.0, step=0.01, value=0.0)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=0, step=1, value=0)

    pieces_new = calculate_pieces(total, barrel, sample_weight, sample_count)
    st.metric("จำนวนชิ้นงานที่คำนวณได้", pieces_new)

    if job["pieces_count"] == 0:
        diff_pct = 0.0
    else:
        diff_pct = abs(pieces_new - job["pieces_count"]) / job["pieces_count"] * 100
    st.metric("เปอร์เซ็นต์คลาดเคลื่อน", f"{diff_pct:.2f}%")

    # ส่ง Telegram ถ้าคลาดเคลื่อนเกิน 2%
    if diff_pct > 2:
        send_telegram_message(
            f"⚠️ แจ้งเตือนความคลาดเคลื่อนน้ำหนักเกิน 2% | แผนก: {dept_to} | WOC: {woc} | Part: {job['part_name']} | "
            f"จำนวนเดิม: {job['pieces_count']} | จำนวนที่รับจริง: {pieces_new} | คลาดเคลื่อน: {diff_pct:.2f}% | Operator: {operator_name}"
        )

    if st.button("รับเข้าและส่งต่อ"):
        if not operator_name.strip():
            st.error("กรุณากรอกชื่อผู้ปฏิบัติงาน")
            return
        insert_job({
            "woc_number": woc,
            "part_name": job["part_name"],
            "operator_name": operator_name,
            "dept_from": dept_to,
            "dept_to": next_status,
            "lot_number": job["lot_number"],
            "total_weight": total,
            "barrel_weight": barrel,
            "sample_weight": sample_weight,
            "sample_count": sample_count,
            "pieces_count": pieces_new,
            "status": f"WIP-{dept_to}"
        })
        update_status(woc, f"{dept_to} Received")
        st.success(f"รับเข้า WOC {woc} เรียบร้อยแล้ว")
        send_telegram_message(f"{dept_to} รับ WOC {woc} โดย {operator_name}")

def work_mode(dept):
    st.subheader(f"{dept} Work")
    operator_name = st.text_input("ชื่อผู้ปฏิบัติงาน (Operator)")
    
    # รับเฉพาะสถานะ On_MC
    status_on_mc = f"{dept}-On_MC"
    df = get_jobs_by_status(status_on_mc)
    if df.empty:
        st.info("ไม่มีงานรอทำ")
        return

    woc = st.selectbox("เลือก WOC", df["woc_number"])
    job = df[df["woc_number"] == woc].iloc[0]

    st.write(f"Part Name: {job['part_name']}")
    st.write(f"Lot Number: {job['lot_number']}")
    st.write(f"จำนวนชิ้นงาน: {job['pieces_count']}")

    machine = st.text_input("ชื่อเครื่องจักร")
    
    if st.button("เริ่มทำงาน"):
        if not operator_name.strip():
            st.error("กรุณากรอกชื่อผู้ปฏิบัติงาน")
            return
        if not machine.strip():
            st.error("กรุณากรอกชื่อเครื่องจักร")
            return
        update_status(woc, f"{dept}-Working")
        st.success(f"เริ่มทำงาน WOC {woc} ที่เครื่อง {machine} โดย {operator_name}")
        send_telegram_message(f"{dept} เริ่มงาน WOC {woc} ที่เครื่อง {machine} โดย {operator_name}")

def completion_mode():
    st.subheader("Completion")
    operator_name = st.text_input("ชื่อผู้ปฏิบัติงาน (Operator)")
    
    # ดึงงานสถานะ Used - FI, Used - OS
    used_statuses = ["Used - FI01", "Used - FI30", "Used - FISM", "Used - OS01", "Used - OS30", "Used - OSSM"]
    df = get_jobs_by_multiple_status(used_statuses)
    if df.empty:
        st.info("ไม่มีงานรอ Completion")
        return

    woc = st.selectbox("เลือก WOC", df["woc_number"])
    ok = st.number_input("จำนวน OK", min_value=0, step=1)
    ng = st.number_input("จำนวน NG", min_value=0, step=1)
    rw = st.number_input("จำนวน Rework", min_value=0, step=1)
    remain = st.number_input("คงเหลือ", min_value=0, step=1)

    if st.button("บันทึก Completion"):
        if not operator_name.strip():
            st.error("กรุณากรอกชื่อผู้ปฏิบัติงาน")
            return
        status = "Completed" if remain == 0 else "Remaining"
        update_status(woc, status)
        send_telegram_message(f"📦 Completion WOC {woc} | OK:{ok}, NG:{ng}, Rework:{rw}, Remain:{remain} | Operator: {operator_name}")
        st.success(f"สถานะอัปเดตเป็น {status}")

def export_mode():
    st.subheader("Export ข้อมูล")
    df = get_all_jobs()
    st.download_button("📥 Export CSV", df.to_csv(index=False).encode("utf-8-sig"), "job_tracking.csv")
    st.dataframe(df)

def report_mode():
    st.subheader("Report")
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
            st.write(f"แผนก {d} : ไม่มีงาน WIP")
        else:
            summary = wip_df.groupby("part_name").agg(
                จำนวนงาน=pd.NamedAgg(column="woc_number", aggfunc="count"),
                จำนวนชิ้นงาน=pd.NamedAgg(column="pieces_count", aggfunc="sum")
            ).reset_index()
            st.write(f"แผนก {d}")
            st.dataframe(summary)

# ====== MAIN ======
def main():
    st.set_page_config("WOC Tracker", layout="wide")
    st.title("🏭 ระบบติดตามงานโรงงาน (Supabase)")

    menu = st.sidebar.selectbox("เลือกโหมด", [
        "Forming Transfer", "Tapping Transfer", "OS Transfer",
        "Tapping Receive", "Final Receive", "OS Receive",
        "Tapping Work", "Final Work",
        "Completion", "Export", "Report"
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

if __name__ == "__main__":
    main()
