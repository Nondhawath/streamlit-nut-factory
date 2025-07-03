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
    try:
        requests.get(url)
    except:
        pass

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

def get_wip_jobs_by_dept(dept):
    conn = get_connection()
    # ดึงสถานะ WIP ของแผนกนั้น
    like_pattern = f'WIP-{dept}%'
    query = "SELECT * FROM job_tracking WHERE status LIKE %s ORDER BY created_at DESC"
    df = pd.read_sql(query, conn, params=(like_pattern,))
    conn.close()
    return df

def get_all_jobs():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM job_tracking ORDER BY created_at DESC", conn)
    conn.close()
    return df

# ====== HELPER ======
def calculate_pieces(total_weight, barrel_weight, sample_weight, sample_count):
    if sample_count == 0:
        return 0
    try:
        pieces = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)
        return math.ceil(pieces)
    except ZeroDivisionError:
        return 0

# ====== RECEIVE MODE (TP, FI, OS) ======
def mode_receive(dept_to):
    st.header(f"{dept_to} Receive")

    # ค้นหาสถานะ Transfer ที่มาจากแผนกก่อนหน้า
    prev_depts_map = {"TP": "FM", "FI": "TP", "OS": ["FM", "TP"]}  # กรณีพิเศษ OS อาจรับจาก FM หรือ TP
    if dept_to == "OS":
        # ดึง status จากทั้ง FM Transfer OS และ TP Transfer OS
        conn = get_connection()
        query = """
            SELECT * FROM job_tracking WHERE 
            (status = %s OR status = %s)
            ORDER BY created_at DESC
        """
        df = pd.read_sql(query, conn, params=("FM Transfer OS", "TP Transfer OS"))
        conn.close()
    else:
        from_dept = prev_depts_map.get(dept_to, "FM")
        if isinstance(from_dept, list):
            from_statuses = [f"{fd} Transfer {dept_to}" for fd in from_dept]
            conn = get_connection()
            qmarks = ','.join(['%s']*len(from_statuses))
            query = f"SELECT * FROM job_tracking WHERE status IN ({qmarks}) ORDER BY created_at DESC"
            df = pd.read_sql(query, conn, params=from_statuses)
            conn.close()
        else:
            from_status = f"{from_dept} Transfer {dept_to}"
            df = get_jobs_by_status(from_status)

    if df.empty:
        st.warning("ไม่มีงานที่รอรับ")
        return

    search = st.text_input("ค้นหา WOC หรือ Part Name", key=f"search_{dept_to}_receive")
    if search:
        df = df[df["woc_number"].str.contains(search, case=False) | df["part_name"].str.contains(search, case=False)]

    woc = st.selectbox("เลือก WOC", df["woc_number"])
    selected = df[df["woc_number"] == woc].iloc[0]

    # เลือกแผนกปลายทางถัดไป (Work แผนกนั้น)
    next_dept_options = {
        "TP": "TP-On_MC",
        "FI": "FI-On_MC",
        "OS": "OS-On_MC"
    }
    next_dept = st.selectbox("เลือกแผนกถัดไป (ปลายทาง)", [next_dept_options[dept_to]])

    total = st.number_input("น้ำหนักรวม", min_value=0.0, value=float(selected["total_weight"]))
    barrel = st.number_input("น้ำหนักถัง", min_value=0.0, value=float(selected["barrel_weight"]))
    sample_w = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0, value=float(selected["sample_weight"]))
    sample_c = st.number_input("จำนวนตัวอย่าง", min_value=0, value=int(selected["sample_count"]))

    pieces_new = calculate_pieces(total, barrel, sample_w, sample_c)
    st.metric("จำนวนชิ้นงานที่คำนวณได้", f"{pieces_new:,}")

    # คำนวณ % แตกต่างกับ pieces ก่อนหน้า
    if selected["pieces_count"] == 0:
        diff_percent = 0.0
    else:
        diff_percent = abs((pieces_new - selected["pieces_count"]) / selected["pieces_count"]) * 100
    st.metric("% แตกต่าง", f"{diff_percent:.2f}%")

    # แจ้งเตือน Telegram ถ้าคลาดเคลื่อนเกิน 2%
    if diff_percent > 2:
        send_telegram_message(
            f"⚠️ พบความคลาดเคลื่อนน้ำหนักเกิน 2% ที่แผนก {dept_to} \n"
            f"พนักงาน: นายคมสันต์\n"
            f"WOC: {woc}\n"
            f"Part Name: {selected['part_name']}\n"
            f"จำนวนที่ส่ง: {selected['pieces_count']}\n"
            f"จำนวนที่รับจริง: {pieces_new}\n"
            f"ความคลาดเคลื่อน: {diff_percent:.2f}%"
        )

    if st.button("รับงาน"):
        insert_job({
            "woc_number": selected["woc_number"],
            "part_name": selected["part_name"],
            "operator_name": "นายคมสันต์",
            "dept_from": dept_to,
            "dept_to": next_dept,
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

# ====== WORK MODE ======
def mode_work(dept):
    st.header(f"{dept} Work")
    df = get_jobs_by_status(f"WIP-{dept}")
    if df.empty:
        st.info("ไม่มีงานรอทำ")
        return
    woc = st.selectbox("เลือก WOC", df["woc_number"])
    selected = df[df["woc_number"] == woc].iloc[0]
    st.write(f"Part Name: {selected['part_name']}")
    st.write(f"Lot Number: {selected['lot_number']}")
    st.write(f"จำนวนชิ้นงาน: {selected['pieces_count']:,}")

    machines = [f"{dept}01", f"{dept}30", f"{dept}SM"]
    machine = st.selectbox("เลือกเครื่อง", machines)

    if st.button("บันทึกการทำงาน"):
        update_status(woc, f"Used - {machine}")
        st.success(f"บันทึกการทำงาน WOC {woc} ที่เครื่อง {machine} แล้ว")
        send_telegram_message(f"{dept} ทำงาน WOC {woc} ที่เครื่อง {machine}")

# ====== OS MODE ======
def mode_os_transfer():
    st.header("OS Transfer")
    prev_woc = st.text_input("WOC ก่อนหน้า (ถ้ามี)")
    dept_to = st.selectbox("แผนกปลายทาง", ["FI"])
    woc = st.text_input("WOC ใหม่")
    part_name = st.text_input("Part Name")
    lot = st.text_input("Lot Number")
    total = st.number_input("น้ำหนักรวม", 0.0)
    barrel = st.number_input("น้ำหนักถัง", 0.0)
    sample_w = st.number_input("น้ำหนักรวมของตัวอย่าง", 0.0)
    sample_c = st.number_input("จำนวนตัวอย่าง", min_value=0)

    if total and barrel and sample_w and sample_c:
        pieces = calculate_pieces(total, barrel, sample_w, sample_c)
        st.metric("จำนวนชิ้นงาน (ปัดขึ้น)", f"{pieces:,}")

    if st.button("บันทึก"):
        status = f"OS Transfer {dept_to}"
        insert_job({
            "woc_number": woc,
            "part_name": part_name,
            "operator_name": "นายคมสันต์",
            "dept_from": "OS",
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
        send_telegram_message(f"OS ส่ง WOC {woc} ไปยัง {dept_to}")

def mode_os_receive():
    mode_receive("OS")

# ====== COMPLETION MODE ======
def mode_completion():
    st.header("Completion")
    # ดึงงานที่สถานะ Used - FI หรือ Used - OS (อาจจะต้องแก้ตามสถานะจริง)
    conn = get_connection()
    query = """
        SELECT * FROM job_tracking 
        WHERE status LIKE 'Used - FI%' OR status LIKE 'Used - OS%'
        ORDER BY created_at DESC
    """
    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        st.info("ไม่มีงานรอ Completion")
        return

    woc = st.selectbox("เลือก WOC", df["woc_number"])
    selected = df[df["woc_number"] == woc].iloc[0]

    st.write(f"Part Name: {selected['part_name']}")
    st.write(f"Lot Number: {selected['lot_number']}")
    st.write(f"จำนวนชิ้นงาน: {selected['pieces_count']:,}")

    ok = st.number_input("จำนวน OK", min_value=0, value=0)
    ng = st.number_input("จำนวน NG", min_value=0, value=0)
    rework = st.number_input("จำนวน Rework", min_value=0, value=0)
    remaining = st.number_input("จำนวนคงเหลือ", min_value=0, value=0)

    if st.button("บันทึก Completion"):
        # เช็คสถานะ
        new_status = "Completed" if remaining == 0 else "ยังคงเหลือ"
        # บันทึกข้อมูล Completion (อาจจะต้องเพิ่มตารางใหม่ หรืออัพเดตใน job_tracking)
        # สมมติอัพเดต status และเก็บข้อมูลเพิ่มเติมลงในฟิลด์อื่นๆได้ (ปรับตามโครงสร้างฐานข้อมูล)
        update_status(woc, new_status)
        st.success(f"บันทึกสถานะ {new_status} สำหรับ WOC {woc}")
        send_telegram_message(f"บันทึก Completion WOC {woc} สถานะ: {new_status}")

# ====== REPORT MODE ======
def mode_report():
    st.header("Report")
    df = get_all_jobs()

    search = st.text_input("ค้นหา Part Name", key="search_report")
    if search:
        df = df[df["part_name"].str.contains(search, case=False)]

    st.dataframe(df)

    # สรุป WIP แยกตามสถานะ
    st.subheader("สรุป WIP แยกตามแผนก")
    depts = ["FM", "TP", "FI", "OS"]
    for d in depts:
        st.write(f"แผนก {d}")
        wip_df = get_wip_jobs_by_dept(d)
        if wip_df.empty:
            st.write("ไม่มีงาน WIP")
        else:
            summary = wip_df.groupby("part_name").agg(
                total_pieces=pd.NamedAgg(column="pieces_count", aggfunc="sum"),
                woc_count=pd.NamedAgg(column="woc_number", aggfunc="nunique")
            ).reset_index()
            st.dataframe(summary)

# ====== DASHBOARD MODE ======
def mode_dashboard():
    st.header("Dashboard")
    df = get_all_jobs()

    dept_filter = st.selectbox("เลือกแผนก", ["ทั้งหมด", "FM", "TP", "FI", "OS"])
    if dept_filter != "ทั้งหมด":
        df = df[(df["dept_from"] == dept_filter) | (df["dept_to"] == dept_filter)]

    if df.empty:
        st.warning("ไม่มีข้อมูล")
        return

    summary = df.groupby(["dept_from", "part_name"]).agg(
        total_pieces=pd.NamedAgg(column="pieces_count", aggfunc="sum"),
        woc_count=pd.NamedAgg(column="woc_number", aggfunc="nunique")
    ).reset_index()

    st.dataframe(summary)

# ====== MAIN ======
def main():
    st.set_page_config(page_title="WOC Job Tracker", layout="wide")
    st.title("📦 ระบบโอนถ่ายงานโรงงาน")

    menu = st.sidebar.selectbox("เลือกโหมด", [
        "Forming Transfer", "Tapping Receive", "Tapping Work",
        "TP Transfer", "Final Inspection Receive", "Final Work", 
        "OS Receive", "OS Transfer", "Completion", "Report", "Dashboard"
    ])

    if menu == "Forming Transfer":
        mode_transfer("FM")
    elif menu == "TP Transfer":
        mode_transfer("TP")
    elif menu == "Tapping Receive":
        mode_receive("TP")
    elif menu == "Tapping Work":
        mode_work("TP")
    elif menu == "Final Inspection Receive":
        mode_receive("FI")
    elif menu == "Final Work":
        mode_work("FI")
    elif menu == "OS Receive":
        mode_os_receive()
    elif menu == "OS Transfer":
        mode_os_transfer()
    elif menu == "Completion":
        mode_completion()
    elif menu == "Report":
        mode_report()
    elif menu == "Dashboard":
        mode_dashboard()

if __name__ == "__main__":
    main()
