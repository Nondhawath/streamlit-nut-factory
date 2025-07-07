import streamlit as st
import psycopg2
import pandas as pd
import requests
import math
from datetime import datetime, timedelta
import numpy as np

# === Connection Pool ===
def get_connection():
    try:
        # ใช้ psycopg2.connect แทนการใช้ Connection Pool
        conn = psycopg2.connect(st.secrets["postgres"]["conn_str"])
        return conn
    except psycopg2.DatabaseError as e:
        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อฐานข้อมูล: {e}")
        return None
# === Telegram Notification ===
def send_telegram_message(message):
    token = st.secrets["telegram"]["token"]
    chat_id = st.secrets["telegram"]["chat_id"]
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}"
    try:
        response = requests.get(url)
        if response.status_code != 200:
            st.error(f"Telegram แจ้งเตือนไม่สำเร็จ: {response.status_code}")
    except Exception as e:
        st.error(f"Telegram แจ้งเตือนไม่สำเร็จ: {e}")

# === Database Operations ===
def insert_job(data):
    # เพิ่มการปรับเวลาเป็น GMT+7
    data["created_at"] = datetime.utcnow() + timedelta(hours=7)  # ปรับเวลาเป็น GMT+7
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
    if total_weight <= barrel_weight or sample_weight <= 0 or sample_count <= 0:
        st.warning("ค่าที่กรอกไม่ถูกต้อง: น้ำหนักรวม, น้ำหนักตัวอย่าง, และจำนวนตัวอย่างต้องเป็นค่าบวกที่ถูกต้อง")
        return 0
    try:
        return math.ceil((total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000))
    except ZeroDivisionError:
        st.error("เกิดข้อผิดพลาดในการคำนวณ: แบ่งด้วยศูนย์")
        return 0

def transfer_mode(dept_from):
    st.header(f"{dept_from} Transfer")
    df_all = get_all_jobs()
    prev_woc = ""
    
    # เลือก WOC ก่อนหน้า
    if dept_from == "TP":
        df = get_jobs_by_status("TP Working")
        prev_woc_options = [""] + list(df["woc_number"].unique())
        prev_woc = st.selectbox("WOC ก่อนหน้า (ถ้ามี)", prev_woc_options)
    elif dept_from == "OS":
        df = get_jobs_by_status("OS Received")
        prev_woc_options = [""] + list(df["woc_number"].unique())
        prev_woc = st.selectbox("WOC ก่อนหน้า (ถ้ามี)", prev_woc_options)
    else:
        st.write("FM Transfer ไม่ต้องเลือก WOC ก่อนหน้า")

    new_woc = st.text_input("WOC ใหม่")

    part_name = ""
    if prev_woc:
        part_name = df_all[df_all["woc_number"] == prev_woc]["part_name"].values[0]
    part_name = st.text_input("Part Name", value=part_name)

    if dept_from == "OS":
        dept_to_options = ["FI"]
    else:
        dept_to_options = ["TP", "FI", "OS"]

    dept_to = st.selectbox("แผนกปลายทาง", dept_to_options)
    lot_number = st.text_input("Lot Number")
    total_weight = st.number_input("น้ำหนักรวม", min_value=0.0, step=0.01)
    barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0, step=0.01)
    sample_weight = st.number_input("น้ำหนักตัวอย่างรวม", min_value=0.0, step=0.01)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=0, step=1, value=0)
    operator_name = st.text_input("ชื่อผู้ใช้งาน (Operator)")

    pieces_count = 0
    if all(v > 0 for v in [total_weight, sample_weight]) and sample_count > 0:
        pieces_count = calculate_pieces(total_weight, barrel_weight, sample_weight, sample_count)
        st.metric("จำนวนชิ้นงาน (คำนวณ)", pieces_count)

    # ตรวจสอบค่าก่อนบันทึก
    if pieces_count > 10000000:  # ขีดจำกัดที่สมมุติว่า 10 ล้าน
        st.error("จำนวนชิ้นงานมากเกินไป")
        return

    if st.button("บันทึก Transfer"):
        if not new_woc.strip():
            st.error("กรุณากรอก WOC ใหม่")
            return
        if pieces_count == 0:
            st.error("กรุณากรอกข้อมูลน้ำหนักและจำนวนตัวอย่างให้ถูกต้อง")
            return

        # ข้อมูลที่ต้องการบันทึก
        data = {
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
            "status": f"{dept_from} Transfer {dept_to}",
            "created_at": datetime.utcnow(),
            "prev_woc_number": prev_woc,  # ฟิลด์ใหม่ที่เก็บ WOC ก่อนหน้า
            "ok_count": st.number_input("จำนวน OK", min_value=0, step=1),
            "ng_count": st.number_input("จำนวน NG", min_value=0, step=1),
            "rework_count": st.number_input("จำนวน Rework", min_value=0, step=1),
            "remain_count": st.number_input("จำนวนคงเหลือ", min_value=0, step=1),
            "machine_name": st.text_input("ชื่อเครื่องจักร")
        }

        insert_job(data)  # ใช้ฟังก์ชัน insert_job เพื่อบันทึกข้อมูลลงฐานข้อมูล

        if prev_woc:
            update_status(prev_woc, "Completed")

        st.success(f"บันทึก {dept_from} Transfer เรียบร้อยแล้ว")
# ฟังก์ชันการตรวจสอบข้อมูลก่อนบันทึก
def validate_data(row):
    # ตรวจสอบค่าว่างในคอลัมน์ที่สำคัญ
    if pd.isnull(row["lot_number"]) or pd.isnull(row["total_weight"]) or pd.isnull(row["barrel_weight"]) or pd.isnull(row["sample_weight"]):
        st.warning(f"คอลัมน์บางคอลัมน์ใน WOC {row['woc_number']} มีค่าว่าง")
        return False
    # ตรวจสอบค่ามากเกินไปในจำนวนชิ้นงานหรือค่าน้ำหนัก
    if row["total_weight"] > 1000000 or row["pieces_count"] > 10000000:
        st.error(f"ข้อมูลใน WOC {row['woc_number']} เกินขีดจำกัด")
        return False
    return True
    
def update_status_to_on_machine(woc_number):
    # เปลี่ยนสถานะของ WOC เป็น "On Machine" พร้อมบันทึกเวลา
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE job_tracking 
            SET status = %s, on_machine_time = %s 
            WHERE woc_number = %s
        """, ("On Machine", datetime.utcnow() + timedelta(hours=7), woc_number))
        conn.commit()

def upload_wip_from_excel():
    st.header("อัพโหลด WIP จากไฟล์ Excel")

    uploaded_file = st.file_uploader("เลือกไฟล์ Excel", type=["xlsx"])

    if uploaded_file is not None:
        # โหลดข้อมูลจากไฟล์ Excel
        df = pd.read_excel(uploaded_file)

        # ตรวจสอบว่า df ถูกโหลดมาหรือไม่
        if df is None or df.empty:
            st.error("ไม่สามารถโหลดข้อมูลจากไฟล์ Excel ได้ หรือไฟล์ว่าง")
            return

        # แทนค่าที่เป็น np.inf และ -np.inf ด้วย NaN
        df.replace([np.inf, -np.inf], np.nan, inplace=True)

        # ===== Mapping ชื่อคอลัมน์ =====
        column_map = {
            "WOC": "woc_number",
            "Part": "part_name",
            "Operator": "operator_name",
            "From": "dept_from",
            "To": "dept_to",
            "Count": "pieces_count",
            "Lot": "lot_number",
            "Total_Weight": "total_weight",
            "Barrel_Weight": "barrel_weight",
            "Sample_Weight": "sample_weight",
            "Sample_Count": "sample_count",
            "OK": "ok_count",
            "NG": "ng_count",
            "Rework": "rework_count",
            "Remain": "remain_count",
            "Machine": "machine_name"
        }

        df.rename(columns=column_map, inplace=True)

        st.write("ข้อมูลในไฟล์ Excel (หลังจัดรูปแบบ):")
        st.dataframe(df.head())

        required_columns = ["woc_number", "part_name", "operator_name", "dept_from", "dept_to", "pieces_count"]

        optional_columns = ["lot_number", "total_weight", "barrel_weight", "sample_weight", "sample_count", "ok_count", "ng_count", "rework_count", "remain_count", "machine_name"]

        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"คอลัมน์ต่อไปนี้ขาดในไฟล์ Excel: {', '.join(missing_columns)}")
            return

        for col in optional_columns:
            if col in df.columns and df[col].isnull().any():
                st.warning(f"คอลัมน์ '{col}' มีข้อมูลที่เป็นค่าว่าง แต่ยังคงสามารถดำเนินการได้")

        def delete_existing_woc(woc_number):
            with get_connection() as conn:
                cur = conn.cursor()
                # ตรวจสอบว่า WOC นี้มีอยู่ในฐานข้อมูลหรือไม่
                cur.execute("SELECT COUNT(*) FROM job_tracking WHERE woc_number = %s", (woc_number,))
                count = cur.fetchone()[0]
                if count > 0:
                    cur.execute("DELETE FROM job_tracking WHERE woc_number = %s", (woc_number,))
                    conn.commit()
                else:
                    st.warning(f"WOC {woc_number} ไม่พบในฐานข้อมูล")

        def safe_int(val):
            try:
                if pd.isna(val):
                    return 0
                return int(float(val))
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการแปลงค่าเป็นจำนวนเต็ม: {e}")
                return 0

        def safe_float(val):
            try:
                if pd.isna(val):
                    return 0.0
                return float(val)
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการแปลงค่าเป็นจำนวนทศนิยม: {e}")
                return 0.0

        for _, row in df.iterrows():
            if pd.isnull(row["woc_number"]):
                continue

            try:
                pieces = safe_int(row["pieces_count"])
            except Exception:
                st.error(f"WOC {row['woc_number']} มีจำนวนชิ้นงานไม่ถูกต้อง: {row['pieces_count']}")
                continue

            delete_existing_woc(row["woc_number"])

            # คำนวณสถานะจาก dept_from และ dept_to
            status = f"{row['dept_from']} Transfer {row['dept_to']}"

            try:
                data = {
                    "woc_number": str(row["woc_number"]),
                    "part_name": str(row["part_name"]),
                    "operator_name": str(row["operator_name"]),
                    "dept_from": str(row.get("dept_from", "")),
                    "dept_to": str(row["dept_to"]),
                    "lot_number": str(row.get("lot_number", "")),
                    "total_weight": safe_float(row.get("total_weight", 0.0)),
                    "barrel_weight": safe_float(row.get("barrel_weight", 0.0)),
                    "sample_weight": safe_float(row.get("sample_weight", 0.0)),
                    "sample_count": safe_int(row.get("sample_count", 0)),
                    "pieces_count": pieces,
                    "status": status,
                    "created_at": datetime.utcnow() + timedelta(hours=7),
                    "prev_woc_number": str(row.get("prev_woc_number", "")),
                    "ok_count": safe_int(row.get("ok_count", 0)),
                    "ng_count": safe_int(row.get("ng_count", 0)),
                    "rework_count": safe_int(row.get("rework_count", 0)),
                    "remain_count": safe_int(row.get("remain_count", 0)),
                    "machine_name": str(row.get("machine_name", "")),
                }
                insert_job(data)
            except Exception as e:
                st.error(f"❌ ไม่สามารถบันทึก WOC {row['woc_number']} ได้: {e}")

        st.success("📥 ข้อมูล WIP ได้ถูกอัปโหลดและบันทึกเรียบร้อยแล้ว")
        st.info("สามารถไปใช้งานต่อได้ในโหมด Receive / Work / Completion / Dashboard / Report")
        report_mode()

# === Receive Mode ===
def receive_mode(dept_to):
    st.header(f"{dept_to} Receive")

    if dept_to == "FI":
        status_filters = ["FM Transfer FI", "TP Transfer FI", "OS Transfer FI"]
    else:
        dept_from_map = {
            "TP": ["FM", "TP Working"],
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

    total_weight = st.number_input("น้ำหนักรวม", min_value=0.0, step=0.01, value=0.0)
    barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0, step=0.01, value=0.0)
    sample_weight = st.number_input("น้ำหนักตัวอย่างรวม", min_value=0.0, step=0.01, value=0.0)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=0, step=1, value=0)
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
            "created_at": datetime.utcnow()
        })
        update_status(woc_selected, f"{dept_to} Received")
        st.success(f"รับ WOC {woc_selected} เรียบร้อยและเปลี่ยนสถานะเป็น {dept_to} Received")
        send_telegram_message(f"{dept_to} รับ WOC {woc_selected} ส่งต่อไปยัง {dept_to_next}")

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

        # เปลี่ยนสถานะจาก TP Working เป็น On Machine
        update_status_to_on_machine(woc_selected)  # เปลี่ยนสถานะไปที่ On Machine
        st.success(f"เปลี่ยนสถานะ WOC {woc_selected} เป็น On Machine")

        # เมื่อการทำงานเสร็จสิ้นและโอนงานไปยังแผนกถัดไป
        update_status(woc_selected, "Completed")  # เปลี่ยนสถานะเป็น Completed
        st.success(f"สถานะ WOC {woc_selected} เป็น Completed")

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

    if st.button("บันทึก Completion"):
        expected_count = job['pieces_count']
        diff_pct = abs(expected_count - total_count) / expected_count * 100 if expected_count > 0 else 0

        if diff_pct > 2:
            st.error(f"จำนวนไม่ตรงกับจำนวนที่รับเข้า (คลาดเคลื่อน {diff_pct:.2f}%)")
            return

        update_status(woc_selected, "Completed")
        st.success(f"บันทึก Completion เรียบร้อย สถานะ WOC {woc_selected} เป็น Completed")

        send_telegram_message(
            f"📦 Completion WOC {woc_selected} | OK: {ok}, NG: {ng}, Rework: {rework}, Remain: {remain} โดย {operator_name} "
            f"(คลาดเคลื่อน: {diff_pct:.2f}%)"
        )
# === Convert DataFrame to Excel ===
@st.cache_data
def convert_df_to_excel(df):
    from io import BytesIO
    import numpy as np

    df_clean = df.copy()
    df_clean.replace([np.inf, -np.inf], np.nan, inplace=True)
    df_clean.fillna("", inplace=True)
    for col in df_clean.columns:
        if df_clean[col].dtype == 'object':
            df_clean[col] = df_clean[col].astype(str)

    excel_buffer = BytesIO()
    df_clean.to_excel(excel_buffer, index=False, engine='openpyxl')
    excel_buffer.seek(0)
    return excel_buffer

# === Report Mode ===
def report_mode():
    st.header("รายงานและสรุป WIP")
    df = get_all_jobs()
    search = st.text_input("ค้นหา Part Name หรือ WOC")
    
    if search:
        df = df[df["part_name"].str.contains(search, case=False) | df["woc_number"].str.contains(search, case=False)]
    
    st.dataframe(df)

    # สรุปข้อมูลแยกตามแผนก
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
    
    # เพิ่มปุ่มดาวน์โหลดรายงานเป็น Excel
    excel_file = convert_df_to_excel(df)
    
    st.download_button(
        label="ดาวน์โหลดเป็นไฟล์ Excel",
        data=excel_file,
        file_name="wip_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# === Dashboard Mode ===
def dashboard_mode():
    st.header("Dashboard WIP รวม")

    # ดึงข้อมูลทั้งหมดจากฐานข้อมูล
    df = get_all_jobs()

    # ตัวเลือกให้เลือกแผนก
    department_options = ["WIP-All", "WIP-TP", "WIP-FM", "WIP-FI", "WIP-OS"]
    selected_dept = st.radio("เลือกแผนกเพื่อดู WIP", department_options)

    # ฟิลเตอร์แสดงตามแผนกที่เลือก
    if selected_dept == "WIP-All":
        # แสดงข้อมูล WIP ทั้งหมด
        wip_map = {
            "WIP-FM": ["FM Transfer TP", "FM Transfer OS"],
            "WIP-TP": ["TP Received", "TP Transfer FI", "TP Working", "WIP-Tapping Work", "TP Transfer OS"],
            "WIP-OS": ["OS Received", "OS Transfer FI"],
            "WIP-FI": ["FI Received", "FI Working", "WIP-Final Work"],
            "Completed": ["Completed"]
        }

        st.subheader("WIP All แยกแผนก")
        
        for wip_name, statuses in wip_map.items():
            st.subheader(f"{wip_name}")
            df_wip = df[df["status"].isin(statuses)]
            total = df_wip["pieces_count"].sum()
            st.markdown(f"**มีจำนวน: {int(total):,} ชิ้น**")

            if not df_wip.empty:
                part_summary = df_wip.groupby("part_name").agg(
                    จำนวนงาน=pd.NamedAgg(column="woc_number", aggfunc="count"),
                    จำนวนชิ้นงาน=pd.NamedAgg(column="pieces_count", aggfunc="sum")
                ).reset_index()
                st.dataframe(part_summary)
            else:
                st.info("ไม่มีข้อมูลในกลุ่มนี้")
    
    elif selected_dept == "WIP-TP":
        status_filters = ["TP Received", "TP Transfer FI", "TP Working", "WIP-Tapping Work", "TP Transfer OS"]
        df_wip = df[df["status"].isin(status_filters)]
        st.subheader("WIP-TP")
        st.write(f"**จำนวนงานที่กำลังดำเนินการ (WIP-TP)**: {len(df_wip)} ชิ้น")
        st.dataframe(df_wip)

    elif selected_dept == "WIP-FM":
        status_filters = ["FM Transfer TP", "FM Transfer OS"]
        df_wip = df[df["status"].isin(status_filters)]
        st.subheader("WIP-FM")
        st.write(f"**จำนวนงานที่กำลังดำเนินการ (WIP-FM)**: {len(df_wip)} ชิ้น")
        st.dataframe(df_wip)

    elif selected_dept == "WIP-FI":
        status_filters = ["FI Received", "FI Working", "WIP-Final Work"]
        df_wip = df[df["status"].isin(status_filters)]
        st.subheader("WIP-FI")
        st.write(f"**จำนวนงานที่กำลังดำเนินการ (WIP-FI)**: {len(df_wip)} ชิ้น")
        st.dataframe(df_wip)

    elif selected_dept == "WIP-OS":
        status_filters = ["OS Received", "OS Transfer FI"]
        df_wip = df[df["status"].isin(status_filters)]
        st.subheader("WIP-OS")
        st.write(f"**จำนวนงานที่กำลังดำเนินการ (WIP-OS)**: {len(df_wip)} ชิ้น")
        st.dataframe(df_wip)

    # ฟิลเตอร์แสดงเฉพาะสถานะ On Machine
    st.subheader("WIP On Machine")
    df_on_machine = df[df["status"] == "On Machine"]

    if not df_on_machine.empty:
        st.write(f"**จำนวนงานที่กำลังทำงานบนเครื่องจักร**: {len(df_on_machine)} ชิ้น")
        st.write("แสดงข้อมูล WIP ที่สถานะเป็น 'On Machine':")
        
        # แสดงข้อมูลที่ต้องการในรูปแบบตาราง
        for _, row in df_on_machine.iterrows():
            part_name = row["part_name"]
            woc_number = row["woc_number"]
            pieces_count = row["pieces_count"]
            on_machine_time = row["on_machine_time"]

            st.markdown(f"### WOC: {woc_number}")
            st.markdown(f"- **Part Name**: {part_name}")
            st.markdown(f"- **จำนวนชิ้นงาน**: {pieces_count}")
            st.markdown(f"- **เริ่มทำงานที่**: {on_machine_time.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        st.info("ไม่มีงานที่กำลังทำงานบนเครื่องจักร")

    # ตัวเลือกในการค้นหา WOC หรือ Part Name
    search = st.text_input("ค้นหา WOC หรือ Part Name")
    if search:
        df = df[df["woc_number"].str.contains(search, case=False, na=False) |
                df["part_name"].str.contains(search, case=False, na=False)]

    # เพิ่มปุ่มดาวน์โหลดรายงานเป็น Excel
    excel_file = convert_df_to_excel(df)
    
    st.download_button(
        label="ดาวน์โหลดเป็นไฟล์ Excel",
        data=excel_file,
        file_name="wip_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# === Admin Management Mode ===
def admin_management():
    st.header("Admin Management")

    # ดึงข้อมูล WOC ทั้งหมดจากฐานข้อมูล
    woc_df = get_all_jobs()  # หรือใช้ get_jobs_by_status("WIP") เพื่อกรองเฉพาะ WIP

    # ตรวจสอบว่ามี WOC ในฐานข้อมูลหรือไม่
    if woc_df.empty:
        st.error("ไม่มีข้อมูล WOC ในฐานข้อมูล")
        return

    # แสดงหมายเลข WOC ใน Dropdown (selectbox) หรือให้เลือกหลายรายการ
    woc_list = woc_df["woc_number"].unique().tolist()

    # ปุ่มเลือกทั้งหมด
    select_all = st.checkbox("เลือกทั้งหมด", value=False)

    # ถ้าเลือกทั้งหมด ให้เลือก WOC ทั้งหมด
    if select_all:
        woc_selected = woc_list
    else:
        woc_selected = st.multiselect("เลือกหมายเลข WOC ที่ต้องการแก้ไขหรือลบ", woc_list)

    if woc_selected:
        # แสดงข้อมูลของ WOC ที่เลือก
        st.write("ข้อมูล WOC ที่เลือก:")
        selected_wocs = woc_df[woc_df["woc_number"].isin(woc_selected)]
        st.dataframe(selected_wocs)

        # สถานะการลบ
        total_to_delete = len(woc_selected)
        deleted_count = 0

        # เพิ่มปุ่มให้ลบ WOC ที่เลือก
        if st.button("ลบ WOC ที่เลือก"):
            for woc_number in woc_selected:
                # ลบ WOC
                with get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("DELETE FROM job_tracking WHERE woc_number = %s", (woc_number,))
                    conn.commit()
                deleted_count += 1
                st.success(f"ลบ WOC {woc_number} เรียบร้อยแล้ว")

            # แสดงสถานะการลบ
            st.info(f"ลบแล้ว {deleted_count}/{total_to_delete} WOC")

            # อัพเดทข้อมูลหลังการลบ
            woc_df = get_all_jobs()  # รีเฟรชข้อมูล WOC หลังจากลบ

        # เพิ่มปุ่มลบทั้งหมด
        if st.button("ลบทั้งหมด"):
            confirm_delete = st.radio("คุณแน่ใจหรือไม่ว่าต้องการลบทั้งหมด?", ["ไม่", "ใช่"])
            if confirm_delete == "ใช่":
                # ลบข้อมูลทั้งหมด
                with get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("DELETE FROM job_tracking")
                    conn.commit()
                st.success("ลบข้อมูลทั้งหมดเรียบร้อยแล้ว")
                woc_df = get_all_jobs()  # รีเฟรชข้อมูล WOC หลังจากลบทั้งหมด

                # แสดงสถานะการลบ
                st.info(f"ลบแล้ว {total_to_delete}/{total_to_delete} WOC")
            else:
                st.warning("การลบทั้งหมดถูกยกเลิก")

    else:
        st.info("กรุณาเลือก WOC ที่ต้องการจัดการ")

# === Main ===
def main():
    st.set_page_config(page_title="WOC Tracker", layout="wide")
    st.title("🏭 ระบบติดตามงานโรงงาน (Supabase + Streamlit)")

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
        "Upload WIP from Excel",  # เพิ่มโหมดใหม่สำหรับการอัปโหลด Excel
        "Admin Management"  # เพิ่มโหมดใหม่สำหรับการจัดการข้อมูล WOC
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
    elif menu == "Upload WIP from Excel":
        upload_wip_from_excel()  # เรียกฟังก์ชันการอัปโหลดข้อมูลจาก Excel
    elif menu == "Admin Management":  # การเลือกโหมด Admin Management
        admin_management()  # เรียกฟังก์ชันจัดการข้อมูล WOC

if __name__ == "__main__":
    main()
