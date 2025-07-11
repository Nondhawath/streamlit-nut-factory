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

def transfer_mode(dept_from):
    st.header(f"{dept_from} Transfer")
    df_all = get_all_jobs()

    # สำหรับ FM สามารถแก้ไขหมายเลข WOC ได้ (ฟังก์ชันนี้เหมาะสำหรับ FM เท่านั้น)
    editable_df = get_jobs_by_status_list([
        "FM Transfer TP", "FM Transfer OS", "FM Transfer FI",
        "TP Transfer FI", "TP Transfer OS",
        "OS Transfer FI","OS Transfer TP"
    ])
    selected_edit_woc = None
    if dept_from == "FM":
        editable_woc_options = [""] + editable_df["woc_number"].unique().tolist()
        selected_edit_woc = st.selectbox("เลือก WOC ที่ต้องการแก้ไขหมายเลข (หรือปล่อยว่างเพื่อเพิ่มใหม่)", editable_woc_options)

    # WOC ก่อนหน้า สำหรับ TP และ OS
    prev_woc = ""
    if dept_from == "TP":
        df_tp_received = get_jobs_by_status("TP Received")
        prev_woc_options = [""] + list(df_tp_received["woc_number"].unique())
        prev_woc = st.selectbox("WOC ก่อนหน้า (ถ้ามี)", prev_woc_options)
    elif dept_from == "OS":
        df_os_received = get_jobs_by_status("OS Received")
        prev_woc_options = [""] + list(df_os_received["woc_number"].unique())
        prev_woc = st.selectbox("WOC ก่อนหน้า (ถ้ามี)", prev_woc_options)
    else:
        st.write("กรอกข้อมูลสำหรับ FM")

    # กรอกข้อมูลฟอร์ม
    if selected_edit_woc:
        job = editable_df[editable_df["woc_number"] == selected_edit_woc].iloc[0]
        new_woc = st.text_input("หมายเลข WOC ใหม่", value="")
        part_name = st.text_input("Part Name", value=job.get("part_name", ""))
        lot_number = st.text_input("Lot Number", value=job.get("lot_number", ""))
        total_weight = st.number_input("น้ำหนักรวม กิโลกรัม", value=job.get("total_weight", 0.0), min_value=0.0, step=0.01)
        barrel_weight = st.number_input("น้ำหนักถัง กิโลกรัม", value=job.get("barrel_weight", 0.0), min_value=0.0, step=0.01)
        sample_weight = st.number_input("น้ำหนักตัวอย่างรวม กรัม", value=job.get("sample_weight", 0.0), min_value=0.0, step=0.01)
        sample_count = st.number_input("จำนวนตัวอย่าง ชิ้น", value=job.get("sample_count", 0), min_value=0, step=1)
        operator_name = st.text_input("ชื่อผู้ใช้งาน (Operator)", value=job.get("operator_name", ""))
        dept_to = st.selectbox("แผนกปลายทาง", ["TP", "FI", "OS"], index=["TP", "FI", "OS"].index(job["dept_to"]))
    else:
        new_woc = st.text_input(f"{dept_from} ระบุหมายเลขเครื่อง / WOC ใหม่")
        part_name_default = ""
        if prev_woc:
            part_name_default = df_all[df_all["woc_number"] == prev_woc]["part_name"].values[0]
        part_name = st.text_input("Part Name", value=part_name_default)
        lot_number = st.text_input("Lot Number")
        total_weight = st.number_input("น้ำหนักรวม กิโลกรัม", min_value=0.0, step=0.01)
        barrel_weight = st.number_input("น้ำหนักถัง กิโลกรัม", min_value=0.0, step=0.01)
        sample_weight = st.number_input("น้ำหนักตัวอย่างรวม กรัม", min_value=0.0, step=0.01)
        sample_count = st.number_input("จำนวนตัวอย่าง ชิ้น", min_value=0, step=1, value=0)
        operator_name = st.text_input("ชื่อผู้ใช้งาน (Operator)")
        dept_to_options = ["TP", "FI", "OS"]
        if dept_from == "TP":
            dept_to_options = ["FI", "OS"]
        elif dept_from == "OS":
            dept_to_options = ["FI","TP"]
        dept_to = st.selectbox("แผนกปลายทาง", dept_to_options)

    if dept_from == dept_to:
        st.error("❌ ไม่สามารถโอนย้ายไปยังแผนกเดียวกันได้")
        return

    # คำนวณจำนวนชิ้น
    pieces_count = 0
    if all(v > 0 for v in [total_weight, sample_weight]) and sample_count > 0:
        pieces_count = calculate_pieces(total_weight, barrel_weight, sample_weight, sample_count)
        st.metric("จำนวนชิ้นงาน (คำนวณ)", pieces_count)

    # ตรวจสอบ WOC ซ้ำในฐานข้อมูล
    existing_wocs = df_all["woc_number"].unique().tolist()
    if selected_edit_woc is None and new_woc.strip() in existing_wocs:
        st.error(f"❌ WOC '{new_woc}' มีอยู่ในระบบแล้ว กรุณาตรวจสอบและกรอกใหม่")
        return

    # บันทึกข้อมูล
    if st.button("บันทึก Transfer"):
        if not new_woc.strip():
            st.error("❌ กรุณากรอก WOC ใหม่")
            return
        if pieces_count == 0:
            st.error("❌ กรุณากรอกข้อมูลน้ำหนักและจำนวนตัวอย่างให้ถูกต้อง")
            return

        if selected_edit_woc:
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("UPDATE job_tracking SET woc_number = %s WHERE woc_number = %s", (new_woc, selected_edit_woc))
                conn.commit()
            st.success(f"✅ อัปเดตหมายเลข WOC จาก {selected_edit_woc} → {new_woc} เรียบร้อย")
        else:
            insert_job({
                "woc_number": new_woc,
                "part_name": part_name,
                "operator_name": operator_name,
                "dept_from": dept_from,
                "dept_to": dept_to,
                "lot_number": lot_number,
                "total_weight": total_weight,
                "barrel_weight": barrel_weight,
                "sample_weight": sample_weight,
                "sample_count": sample_count,
                "pieces_count": pieces_count,
                "prev_woc_number": prev_woc if prev_woc else None,
                "status": f"{dept_from} Transfer {dept_to}",
                "created_at": datetime.utcnow()
            })

            if prev_woc:
                update_status(prev_woc, "Completed")

            st.success(f"✅ บันทึก {dept_from} Transfer เรียบร้อยแล้ว")
            
# === ฟังก์ชันช่วยอัปเดตสถานะรายการก่อนหน้าให้ Completed ===
def mark_previous_entries_completed(woc_number, latest_created_at):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE job_tracking
            SET status = 'Completed'
            WHERE woc_number = %s AND created_at < %s AND status != 'Completed'
        """, (woc_number, latest_created_at))
        conn.commit()

# === Receive Mode ===
def receive_mode(dept_to):
    st.header(f"{dept_to} Receive")

    if dept_to == "FI":
        status_filters = ["FM Transfer FI", "TP Transfer FI", "OS Transfer FI"]
    else:
        dept_from_map = {
            "TP": ["FM", "TP Working", "OS"],  # เพิ่ม "OS"
            "OS": ["FM", "TP"]
        }
        from_depts = dept_from_map.get(dept_to, [])
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

    total_weight = st.number_input("น้ำหนักรวม กิโลกรัม", min_value=0.0, step=0.01, value=0.0)
    barrel_weight = st.number_input("น้ำหนักถัง กิโลกรัม", min_value=0.0, step=0.01, value=0.0)
    sample_weight = st.number_input("น้ำหนักตัวอย่างรวม กรัม", min_value=0.0, step=0.01, value=0.0)
    sample_count = st.number_input("จำนวนตัวอย่าง 3 ชิ้น", min_value=0, step=1, value=0)
    pieces_new = calculate_pieces(total_weight, barrel_weight, sample_weight, sample_count)
    st.metric("จำนวนชิ้นงานที่คำนวณได้", pieces_new)

    try:
        diff_pct = abs(pieces_new - job["pieces_count"]) / job["pieces_count"] * 100 if job["pieces_count"] > 0 else 0
    except Exception:
        diff_pct = 0
    st.metric("% คลาดเคลื่อน", f"{diff_pct:.2f}%")

    if diff_pct > 2:
        send_telegram_message(
            f"⚠️ ความคลาดเคลื่อนน้ำหนักเกิน 2% | แผนก: {dept_to} | WOC: {woc_selected} | Part: {job['part_name']} | "
            f"จำนวนเดิม: {job['pieces_count']} | จำนวนที่รับจริง: {pieces_new} | คลาดเคลื่อน: {diff_pct:.2f}%"
        )

    operator_name = st.text_input("ชื่อผู้ใช้งาน (Operator)")

    if dept_to == "TP":
        dept_to_next = st.selectbox("แผนกถัดไป", ["Tapping Work"])
    elif dept_to == "FI":
        dept_to_next = "Final Work"
        st.markdown(f"- แผนกถัดไป: {dept_to_next}")
    elif dept_to == "OS":
        dept_to_next = st.selectbox("แผนกถัดไป", ["OS Transfer"])
    else:
        dept_to_next = ""
        st.markdown("- กรุณาระบุแผนกถัดไป")

    if st.button("รับเข้าและส่งต่อ"):
        if not dept_to_next:
            st.error("กรุณาเลือกแผนกถัดไป")
            return

        next_status = f"WIP-{dept_to_next}"
        now = datetime.utcnow()

        insert_job({
            "woc_number": woc_selected,
            "part_name": job["part_name"],
            "operator_name": operator_name,
            "dept_from": dept_to,
            "dept_to": dept_to_next,
            "lot_number": job["lot_number"],
            "total_weight": total_weight,
            "barrel_weight": barrel_weight,
            "sample_weight": sample_weight,
            "sample_count": sample_count,
            "pieces_count": pieces_new,
            "status": next_status,
            "created_at": now
        })

        update_status(woc_selected, f"{dept_to} Received")
        mark_previous_entries_completed(woc_selected, now)

        st.success(f"รับ WOC {woc_selected} เรียบร้อยและเปลี่ยนสถานะเป็น {dept_to} Received")
        send_telegram_message(f"{dept_to} รับ WOC {woc_selected} ส่งต่อไปยัง {dept_to_next}")

# === Work Mode ===
def insert_job(data):
    with get_connection() as conn:
        cur = conn.cursor()
        keys = ', '.join(data.keys())
        values = ', '.join(['%s'] * len(data))
        sql = f"INSERT INTO job_tracking ({keys}) VALUES ({values})"
        try:
            cur.execute(sql, list(data.values()))
            conn.commit()
        except Exception as e:
            st.error(f"SQL Insert Error: {e}")
            raise

# === Work Mode ===
def work_mode(dept):
    st.header(f"{dept} Work")

    status_working = {
        "TP": "TP Received",
        "FI": "FI Received"
    }
    status_filter = status_working.get(dept, "")

    if not status_filter:
        st.warning("ไม่มีสถานะสำหรับโหมดนี้")
        return

    df = get_jobs_by_status(status_filter)
    df = df.sort_values('created_at', ascending=False)
    df = df.drop_duplicates(subset=['woc_number'], keep='first')

    if df.empty:
        st.info("ไม่มีงานรอทำ")
        return

    woc_list = df["woc_number"].tolist()
    woc_selected = st.selectbox("เลือก WOC ที่จะทำงาน", woc_list)
    job = df[df["woc_number"] == woc_selected].iloc[0]

    st.markdown(f"- **Part Name:** {job['part_name']}")
    st.markdown(f"- **Lot Number:** {job['lot_number']}")
    st.markdown(f"- **จำนวนชิ้นงานเดิม:** {job['pieces_count']}")

    machine_name = st.text_input("ชื่อเครื่องจักร")
    operator_name = st.text_input("ชื่อผู้ใช้งาน (Operator)")

    if st.button("เริ่มทำงาน"):
        if not machine_name.strip():
            st.error("กรุณากรอกชื่อเครื่องจักร")
            return
        if not operator_name.strip():
            st.error("กรุณากรอกชื่อผู้ใช้งาน")
            return

        on_machine_time = datetime.utcnow()

        # เพิ่มส่วนนี้ เพื่ออัปเดตสถานะรายการก่อนหน้าให้เป็น Completed
        mark_previous_entries_completed(woc_selected, on_machine_time)

        data = {
            "woc_number": str(woc_selected),
            "part_name": str(job["part_name"]),
            "operator_name": str(operator_name),
            "dept_from": str(job["dept_from"]),
            "dept_to": str(job["dept_to"]),
            "lot_number": str(job["lot_number"]),
            "total_weight": float(job["total_weight"]) if job["total_weight"] is not None else None,
            "barrel_weight": float(job["barrel_weight"]) if job["barrel_weight"] is not None else None,
            "sample_weight": float(job["sample_weight"]) if job["sample_weight"] is not None else None,
            "sample_count": int(job["sample_count"]) if job["sample_count"] is not None else None,
            "pieces_count": float(job["pieces_count"]) if job["pieces_count"] is not None else None,
            "machine_name": machine_name if machine_name.strip() != "" else None,
            "on_machine_time": on_machine_time,
            "status": f"{dept} Working",
            "created_at": on_machine_time
        }

        insert_job(data)

        st.success(f"เริ่มทำงาน WOC {woc_selected} ที่เครื่อง {machine_name}")
        send_telegram_message(f"{dept} เริ่มงาน WOC {woc_selected} ที่เครื่อง {machine_name} โดย {operator_name}")


# === Completion Mode ===
def completion_mode():
    st.header("Completion")
    df = get_jobs_by_status("FI Working")

    if df.empty:
        st.info("ไม่มีงานรอ Completion")
        return

    woc_list = df["woc_number"].tolist()
    woc_selected = st.selectbox("เลือก WOC ที่จะทำ Completion", woc_list)
    job = df[df["woc_number"] == woc_selected].iloc[0]

    st.markdown(f"- **Part Name:** {job['part_name']}")
    st.markdown(f"- **Lot Number:** {job['lot_number']}")
    st.markdown(f"- **จำนวนชิ้นงานเดิม:** {job['pieces_count']}")

    ok = st.number_input("จำนวน OK", min_value=0, step=1)
    ng = st.number_input("จำนวน NG", min_value=0, step=1)
    rework = st.number_input("จำนวน Rework", min_value=0, step=1)
    remain = st.number_input("จำนวนคงเหลือ", min_value=0, step=1)

    operator_name = st.text_input("ชื่อผู้ใช้งาน (Operator)")

    total_count = ok + ng + rework + remain
    expected_count = job['pieces_count']
    try:
        diff_pct = abs(expected_count - total_count) / expected_count * 100 if expected_count > 0 else 0
    except ZeroDivisionError:
        diff_pct = 0

    if st.button("บันทึก Completion"):
        if diff_pct > 2:
            st.error(f"❌ จำนวนไม่ตรงกับจำนวนที่รับเข้า (คลาดเคลื่อน {diff_pct:.2f}%)")
            return

        # ===== เริ่มเก็บข้อมูลสะสม =====
        df_all = get_all_jobs()
        df_completed = df_all[(df_all["woc_number"] == woc_selected) & (df_all["status"] == "Completed")]

        cumulative_completed = df_completed["latest_completion_count"].sum()
        latest_completion = ok + ng + rework
        total_cumulative = cumulative_completed + latest_completion
        remaining_after_completion = expected_count - total_cumulative

        # กำหนดสถานะใหม่
        if remaining_after_completion > 0:
            status = "FI Received"
        else:
            status = "Completed"

        now = datetime.utcnow()

        # อัปเดตรายการก่อนหน้าให้ Completed
        mark_previous_entries_completed(woc_selected, now)

        insert_job({
            "woc_number": woc_selected,
            "part_name": job["part_name"],
            "operator_name": operator_name,
            "dept_from": job["dept_from"],
            "dept_to": "WH",
            "lot_number": job["lot_number"],
            "pieces_count": total_count,
            "ok_count": ok,
            "ng_count": ng,
            "rework_count": rework,
            "remain_count": remain,
            "latest_completion_count": latest_completion,
            "cumulative_completed_count": total_cumulative,
            "remaining_after_completion": remaining_after_completion,
            "status": status,
            "created_at": now
        })

        if status == "Completed":
            st.success(f"📦 งานเสร็จสิ้นแล้ว ส่ง WH เรียบร้อย WOC: {woc_selected}")
        else:
            st.warning(f"⚠️ งานยังไม่เสร็จ เหลืออีก {remaining_after_completion} ชิ้น → กลับไป FI Received")

        send_telegram_message(
            f"📦 Completion WOC {woc_selected} | OK: {ok}, NG: {ng}, Rework: {rework}, Remain: {remain} โดย {operator_name} "
            f"(คลาดเคลื่อน: {diff_pct:.2f}%) | เหลืออีก: {remaining_after_completion} ชิ้น | Status: {status}"
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

    # เพิ่มช่องค้นหา
    search = st.text_input("ค้นหา WOC หรือ Part Name")
    if search:
        df = df[df["woc_number"].str.contains(search, case=False, na=False) |
                df["part_name"].str.contains(search, case=False, na=False)]

    # หาค่าที่เป็นรายการล่าสุดของแต่ละ WOC โดยอิงจาก created_at ล่าสุด
    df_latest = df.sort_values('created_at', ascending=False).drop_duplicates(subset=['woc_number'], keep='first')

    # แผนกและสถานะที่นับว่าเป็น WIP
    wip_map = {
        "WIP-FM": [
            "FM Transfer TP", "FM Transfer OS" ,"FM Transfer FI"
        ],
        "WIP-TP": [
            "TP Received", "TP Transfer FI", "TP Working", "WIP-Tapping Work", "TP Transfer OS"
        ],
        "WIP-OS": [
            "OS Received", "OS Transfer FI"
        ],
        "WIP-FI": [
            "FI Received", "FI Working", "WIP-Final Work"
        ],
        "Completed": [
            "Completed"
        ]
    }

    for wip_name, statuses in wip_map.items():
        st.subheader(f"{wip_name}")
        df_wip = df_latest[df_latest["status"].isin(statuses)]
        total = df_wip["pieces_count"].sum()
        st.markdown(f"**มีจำนวน: {int(total):,} ชิ้น**")

        if not df_wip.empty:
            part_summary = df_wip.groupby(["part_name", "status"]).agg(
                จำนวนงาน=pd.NamedAgg(column="woc_number", aggfunc="count"),
                จำนวนชิ้นงาน=pd.NamedAgg(column="pieces_count", aggfunc="sum")
            ).reset_index()
            
            st.dataframe(part_summary)

        else:
            st.info("ไม่มีข้อมูลในกลุ่มนี้")
# === Admin Management Mode ===
def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def admin_mode():
    st.header("🛠️ Admin Management - แก้ไข/ลบข้อมูล")

    # รหัสผ่านก่อนเข้าถึงโหมดนี้
    password = st.text_input("กรุณาใส่รหัสผ่านเพื่อเข้าถึง", type="password")
    if password != "0":
        st.warning("ใส่รหัสผ่านเพื่อเข้าถึงโหมดนี้")
        return

    st.success("✅ เข้าสู่โหมดผู้ดูแลระบบแล้ว")

    df = get_all_jobs()
    search = st.text_input("🔍 ค้นหา WOC หรือ Part Name")

    if search:
        df = df[df["woc_number"].str.contains(search, case=False, na=False) |
                df["part_name"].str.contains(search, case=False, na=False)]

    if df.empty:
        st.warning("ไม่พบข้อมูลที่ค้นหา")
        return

    woc_selected = st.selectbox("เลือก WOC เพื่อแก้ไข/ลบ", df["woc_number"].unique())
    job = df[df["woc_number"] == woc_selected].iloc[0]

    with st.expander("📄 รายละเอียดปัจจุบัน"):
        st.json(job.to_dict(), expanded=False)

    st.subheader("📝 แก้ไขข้อมูล")
    part_name = st.text_input("Part Name", job["part_name"])
    lot_number = st.text_input("Lot Number", job["lot_number"])
    total_weight = st.number_input("น้ำหนักรวม กิโลกรัม", min_value=0.0, value=float(job["total_weight"] or 0), step=0.01)
    barrel_weight = st.number_input("น้ำหนักถัง กิโลกรัม", min_value=0.0, value=float(job["barrel_weight"] or 0), step=0.01)
    sample_weight = st.number_input("น้ำหนักตัวอย่างรวม กรัม", min_value=0.0, value=float(job["sample_weight"] or 0), step=0.01)
    sample_count = st.number_input("จำนวนตัวอย่าง 3 ชิ้น", min_value=0, value=safe_int(job["sample_count"]), step=1)
    pieces_count = st.number_input("จำนวนชิ้นงาน", min_value=0, value=safe_int(job["pieces_count"]), step=1)
    operator_name = st.text_input("ชื่อผู้ใช้งาน", job["operator_name"])
    status = st.text_input("สถานะ", job["status"])
    dept_from = st.text_input("แผนกต้นทาง", job["dept_from"])
    dept_to = st.text_input("แผนกปลายทาง", job["dept_to"])

    machine_name = st.text_input("ชื่อเครื่องจักร", job.get("machine_name", ""))

    # ตรวจสอบ on_machine_time
    on_machine_time_str = ""
    if pd.notnull(job.get("on_machine_time")):
        try:
            on_machine_time_str = job["on_machine_time"].strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            on_machine_time_str = str(job["on_machine_time"])
    on_machine_time_input = st.text_input("เวลาเริ่มงาน (YYYY-MM-DD HH:MM:SS)", on_machine_time_str)

    ok_count = st.number_input("จำนวน OK", min_value=0, value=safe_int(job.get("ok_count", 0)), step=1)
    ng_count = st.number_input("จำนวน NG", min_value=0, value=safe_int(job.get("ng_count", 0)), step=1)
    rework_count = st.number_input("จำนวน Rework", min_value=0, value=safe_int(job.get("rework_count", 0)), step=1)
    remain_count = st.number_input("จำนวนคงเหลือ", min_value=0, value=safe_int(job.get("remain_count", 0)), step=1)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 อัปเดตข้อมูล"):
            try:
                on_machine_time = datetime.strptime(on_machine_time_input, "%Y-%m-%d %H:%M:%S") if on_machine_time_input else None
            except ValueError:
                st.error("รูปแบบวันที่เวลาไม่ถูกต้อง (ต้องเป็น YYYY-MM-DD HH:MM:SS)")
                return

            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE job_tracking SET
                        part_name = %s,
                        lot_number = %s,
                        total_weight = %s,
                        barrel_weight = %s,
                        sample_weight = %s,
                        sample_count = %s,
                        pieces_count = %s,
                        operator_name = %s,
                        status = %s,
                        dept_from = %s,
                        dept_to = %s,
                        machine_name = %s,
                        on_machine_time = %s,
                        ok_count = %s,
                        ng_count = %s,
                        rework_count = %s,
                        remain_count = %s
                    WHERE woc_number = %s
                """, (
                    part_name, lot_number, total_weight, barrel_weight,
                    sample_weight, sample_count, pieces_count, operator_name,
                    status, dept_from, dept_to,
                    machine_name, on_machine_time,
                    ok_count, ng_count, rework_count, remain_count,
                    woc_selected
                ))
                conn.commit()
            st.success(f"อัปเดต WOC {woc_selected} เรียบร้อยแล้ว")

    with col2:
        confirm = st.checkbox("ยืนยันว่าต้องการลบจริง ๆ")
        if st.button("🗑️ ลบข้อมูลนี้") and confirm:
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM job_tracking WHERE woc_number = %s", (woc_selected,))
                conn.commit()
            st.success(f"ลบ WOC {woc_selected} เรียบร้อยแล้ว")

def on_machine_mode():
    st.header("🛠️ งานที่กำลัง On Machine")

    df = get_all_jobs()

    # กรองเฉพาะงานที่สถานะ TP Working หรือ FI Working และมีเวลาเริ่มงาน
    working_statuses = ["TP Working", "FI Working"]
    df_on_machine = df[
        df["status"].isin(working_statuses) &
        df["on_machine_time"].notnull() &
        (df["status"] != "Completed")
    ].copy()

    if df_on_machine.empty:
        st.info("ไม่มีงานที่กำลัง On Machine")
        return

    # ✅ เหลือเฉพาะรายการล่าสุดต่อเครื่อง
    df_on_machine = df_on_machine.sort_values("created_at", ascending=False)
    df_on_machine = df_on_machine.drop_duplicates(subset=["machine_name"], keep="first")

    # Map dept_to กลับเป็นแผนกย่อ เพื่อใช้ในการกรอง
    df_on_machine["dept_group"] = df_on_machine["dept_to"].replace({
        "Tapping Work": "TP",
        "Final Work": "FI"
    })

    selected_dept = st.selectbox("เลือกแผนก", ["ทั้งหมด", "TP", "FI"])
    if selected_dept != "ทั้งหมด":
        df_on_machine = df_on_machine[df_on_machine["dept_group"] == selected_dept]

    df_show = df_on_machine[[
        "machine_name", "woc_number", "part_name", "pieces_count", "operator_name", "on_machine_time"
    ]].rename(columns={
        "machine_name": "ชื่อเครื่องจักร",
        "woc_number": "WOC",
        "part_name": "ชื่อชิ้นงาน",
        "pieces_count": "จำนวน",
        "operator_name": "ชื่อพนักงาน",
        "on_machine_time": "เวลาเริ่มงาน"
    })

    st.dataframe(df_show.sort_values("เวลาเริ่มงาน", ascending=False), use_container_width=True)

# === Main ===
def main():
    st.set_page_config(page_title="WOC Tracker", layout="wide")
    st.title("🏭 SCS WIP Management")

    menu = st.sidebar.selectbox("เลือกโหมด", [
        "Forming Transfer",
        "Tapping Transfer",
        "Tapping Receive",
        "Tapping Work",
        "OS Transfer",
        "OS Receive",
        "Final Receive",
        "Final Work",
        "Completion",
        "Report",
        "Dashboard",
         "🔧 On Machine",
        "Admin Management"
    ])

    if menu == "Forming Transfer":
        transfer_mode("FM")
    elif menu == "Tapping Transfer":
        transfer_mode("TP")
    elif menu == "Tapping Receive":
        receive_mode("TP")
    elif menu == "Tapping Work":
        work_mode("TP")
    elif menu == "OS Transfer":
        transfer_mode("OS")
    elif menu == "OS Receive":
        receive_mode("OS")
    elif menu == "Final Receive":
        receive_mode("FI")
    elif menu == "Final Work":
        work_mode("FI")
    elif menu == "Completion":
        completion_mode()
    elif menu == "Report":
        report_mode()
    elif menu == "Dashboard":
        dashboard_mode()
    elif menu == "🔧 On Machine":
        on_machine_mode()
    elif menu == "Admin Management":
        admin_mode()
    
if __name__ == "__main__":
    main()
