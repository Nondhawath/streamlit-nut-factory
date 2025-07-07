import streamlit as st
import psycopg2
import pandas as pd
import requests
import math
from datetime import datetime, timedelta
import numpy as np
import io

# แทนค่าที่เป็น inf, -inf ด้วย NaN และเติมค่าว่างใน df (ถ้ามี)
# (หากมี df อยู่แล้ว ควรเรียกในส่วนที่เหมาะสม)
# df.replace([np.inf, -np.inf], np.nan, inplace=True)
# df.fillna("", inplace=True)

# === Database Connection ===
def get_connection():
    try:
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
    # เพิ่มเวลาสร้างเป็น UTC+7
    data["created_at"] = datetime.utcnow() + timedelta(hours=7)
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

# === Helper Functions ===
def calculate_pieces(total_weight, barrel_weight, sample_weight, sample_count):
    if total_weight <= barrel_weight or sample_weight <= 0 or sample_count <= 0:
        st.warning("ค่าที่กรอกไม่ถูกต้อง: น้ำหนักรวม, น้ำหนักตัวอย่าง, และจำนวนตัวอย่างต้องเป็นค่าบวกที่ถูกต้อง")
        return 0
    try:
        return math.ceil((total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000))
    except ZeroDivisionError:
        st.error("เกิดข้อผิดพลาดในการคำนวณ: แบ่งด้วยศูนย์")
        return 0

def validate_data(row):
    # ตรวจสอบค่าว่างในคอลัมน์สำคัญ
    if pd.isnull(row["lot_number"]) or pd.isnull(row["total_weight"]) or pd.isnull(row["barrel_weight"]) or pd.isnull(row["sample_weight"]):
        st.warning(f"คอลัมน์บางคอลัมน์ใน WOC {row['woc_number']} มีค่าว่าง")
        return False
    # ตรวจสอบค่ามากเกินไป
    if row["total_weight"] > 1000000 or row["pieces_count"] > 10000000:
        st.error(f"ข้อมูลใน WOC {row['woc_number']} เกินขีดจำกัด")
        return False
    return True

# === Mode: Transfer ===
def transfer_mode(dept_from):
    st.header(f"{dept_from} Transfer")
    df_all = get_all_jobs()
    prev_woc = ""

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

    if pieces_count > 10000000:
        st.error("จำนวนชิ้นงานมากเกินไป")
        return

    if st.button("บันทึก Transfer"):
        if not new_woc.strip():
            st.error("กรุณากรอก WOC ใหม่")
            return
        if pieces_count == 0:
            st.error("กรุณากรอกข้อมูลน้ำหนักและจำนวนตัวอย่างให้ถูกต้อง")
            return

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
            "prev_woc_number": prev_woc,
            "ok_count": st.number_input("จำนวน OK", min_value=0, step=1),
            "ng_count": st.number_input("จำนวน NG", min_value=0, step=1),
            "rework_count": st.number_input("จำนวน Rework", min_value=0, step=1),
            "remain_count": st.number_input("จำนวนคงเหลือ", min_value=0, step=1),
            "machine_name": st.text_input("ชื่อเครื่องจักร")
        }

        insert_job(data)

        if prev_woc:
            update_status(prev_woc, "Completed")

        st.success(f"บันทึก {dept_from} Transfer เรียบร้อยแล้ว")

# === Mode: Upload WIP from Excel ===
def upload_wip_from_excel():
    st.header("อัพโหลด WIP จากไฟล์ Excel")

    uploaded_file = st.file_uploader("เลือกไฟล์ Excel", type=["xlsx"])

    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)

        # Mapping ชื่อคอลัมน์
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
                cur.execute("DELETE FROM job_tracking WHERE woc_number = %s", (woc_number,))
                conn.commit()

        def safe_int(val):
            try:
                if pd.isna(val):
                    return 0
                return int(float(val))
            except:
                return 0

        def safe_float(val):
            try:
                if pd.isna(val):
                    return 0.0
                return float(val)
            except:
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

# === Mode: Receive ===
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
        report_mode()

# === Mode: Work ===
def work_mode(dept):
    st.header(f"{dept} Work")

    status_wip = f"WIP-{dept}"
    df = get_jobs_by_status(status_wip)

    if df.empty:
        st.warning(f"ไม่มีงานในสถานะ {status_wip}")
        return

    woc_list = df["woc_number"].tolist()
    woc_selected = st.selectbox("เลือก WOC เพื่อเริ่มทำงาน", woc_list)
    job = df[df["woc_number"] == woc_selected].iloc[0]

    st.markdown(f"- **Part Name:** {job['part_name']}")
    st.markdown(f"- **Lot Number:** {job['lot_number']}")
    st.markdown(f"- **จำนวนชิ้นงาน:** {job['pieces_count']}")

    ok_count = st.number_input("จำนวน OK", min_value=0, max_value=job["pieces_count"], step=1)
    ng_count = st.number_input("จำนวน NG", min_value=0, max_value=job["pieces_count"] - ok_count, step=1)
    rework_count = st.number_input("จำนวน Rework", min_value=0, max_value=job["pieces_count"] - ok_count - ng_count, step=1)
    remain_count = job["pieces_count"] - ok_count - ng_count - rework_count
    st.markdown(f"- **จำนวนคงเหลือ:** {remain_count}")

    operator_name = st.text_input("ชื่อผู้ใช้งาน (Operator)")

    if st.button("บันทึกงาน"):
        if ok_count + ng_count + rework_count > job["pieces_count"]:
            st.error("จำนวนรวม OK, NG, Rework เกินจำนวนชิ้นงาน")
            return

        update_status(woc_selected, f"{dept} Working")

        insert_job({
            "woc_number": woc_selected,
            "part_name": job["part_name"],
            "operator_name": operator_name,
            "dept_from": dept,
            "dept_to": dept,
            "lot_number": job["lot_number"],
            "ok_count": ok_count,
            "ng_count": ng_count,
            "rework_count": rework_count,
            "remain_count": remain_count,
            "status": f"{dept} Work",
            "created_at": datetime.utcnow()
        })

        st.success("บันทึกข้อมูลงานเรียบร้อย")

# === Mode: Completion ===
def completion_mode():
    st.header("Completion")

    df = get_jobs_by_status("FI Work")

    if df.empty:
        st.warning("ไม่มีงานสำหรับ Complete")
        return

    woc_list = df["woc_number"].tolist()
    woc_selected = st.selectbox("เลือก WOC", woc_list)
    job = df[df["woc_number"] == woc_selected].iloc[0]

    st.markdown(f"- **Part Name:** {job['part_name']}")
    st.markdown(f"- **Lot Number:** {job['lot_number']}")
    st.markdown(f"- **จำนวนชิ้นงาน:** {job['pieces_count']}")

    ok_count = st.number_input("จำนวน OK", min_value=0, max_value=job["pieces_count"], step=1)
    ng_count = st.number_input("จำนวน NG", min_value=0, max_value=job["pieces_count"] - ok_count, step=1)
    rework_count = st.number_input("จำนวน Rework", min_value=0, max_value=job["pieces_count"] - ok_count - ng_count, step=1)
    remain_count = job["pieces_count"] - ok_count - ng_count - rework_count

    if remain_count == 0:
        status = "Completed"
    else:
        status = "ยังคงเหลือ"

    st.markdown(f"- **สถานะ:** {status}")

    operator_name = st.text_input("ชื่อผู้ใช้งาน (Operator)")

    if st.button("บันทึก Completion"):
        insert_job({
            "woc_number": woc_selected,
            "part_name": job["part_name"],
            "operator_name": operator_name,
            "dept_from": "FI",
            "dept_to": "WH",
            "lot_number": job["lot_number"],
            "ok_count": ok_count,
            "ng_count": ng_count,
            "rework_count": rework_count,
            "remain_count": remain_count,
            "status": status,
            "created_at": datetime.utcnow()
        })
        update_status(woc_selected, status)
        st.success("บันทึกสถานะ Completion เรียบร้อย")

# === Mode: Report ===
def report_mode():
    st.header("รายงาน")

    df = get_all_jobs()
    st.dataframe(df)

    excel_data = convert_df_to_excel(df)
    st.download_button(label="ดาวน์โหลดรายงานเป็น Excel", data=excel_data, file_name="job_report.xlsx")

# === Excel Converter Helper ===
@st.cache_data
def convert_df_to_excel(df):
    from io import BytesIO
    import numpy as np

    df_clean = df.copy()

    # จัดการ NaN, inf, -inf
    df_clean.replace([np.inf, -np.inf], np.nan, inplace=True)
    df_clean.fillna("", inplace=True)

    # แปลงทุกคอลัมน์ให้เป็น string ปลอดภัย
    for col in df_clean.columns:
        df_clean[col] = df_clean[col].astype(str)

    # แปลง datetime เป็น string ด้วย
    for col in df_clean.columns:
        if df_clean[col].str.contains("Timestamp|datetime|NaT", case=False).any():
            df_clean[col] = pd.to_datetime(df_clean[col], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
            df_clean[col].fillna("", inplace=True)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_clean.to_excel(writer, index=False, sheet_name="Report")

    output.seek(0)
    return output
    
# === Admin Management ===
def admin_management():
    st.header("Admin Management")

    df = get_all_jobs()
    st.dataframe(df)

    woc_selected = st.text_input("กรอก WOC เพื่อแก้ไขข้อมูล")

    if woc_selected:
        job_df = df[df["woc_number"] == woc_selected]
        if job_df.empty:
            st.warning("ไม่พบข้อมูล WOC ที่ระบุ")
            return

        job = job_df.iloc[0]

        # ตัวอย่างแก้ไข fields
        part_name = st.text_input("Part Name", value=job["part_name"])
        operator_name = st.text_input("Operator Name", value=job["operator_name"])
        status = st.text_input("Status", value=job["status"])

        if st.button("บันทึกข้อมูลแก้ไข"):
            # สำหรับแก้ไขจริงควรใช้ SQL UPDATE แทน insert ใหม่
            st.warning("ฟังก์ชันแก้ไขยังไม่สมบูรณ์ (ควร implement UPDATE SQL)")

# === Main Application ===
def main():
    st.title("ระบบจัดการงานในโรงงาน")

    menu = [
        "FM Transfer", "TP Transfer", "OS Transfer",
        "FM Receive", "TP Receive", "FI Receive",
        "TP Work", "FI Work",
        "Completion",
        "Upload WIP Excel",
        "Report",
        "Dashboard",  # ✅ เพิ่มตรงนี้
        "Admin Management"
    ]

    choice = st.sidebar.selectbox("เลือกโหมด", menu)

    if choice == "FM Transfer":
        transfer_mode("FM")
    elif choice == "TP Transfer":
        transfer_mode("TP")
    elif choice == "OS Transfer":
        transfer_mode("OS")
    elif choice == "FM Receive":
        receive_mode("FM")
    elif choice == "TP Receive":
        receive_mode("TP")
    elif choice == "FI Receive":
        receive_mode("FI")
    elif choice == "TP Work":
        work_mode("TP")
    elif choice == "FI Work":
        work_mode("FI")
    elif choice == "Completion":
        completion_mode()
    elif choice == "Upload WIP Excel":
        upload_wip_from_excel()
    elif choice == "Report":
        report_mode()
    elif choice == "Dashboard":  # ✅ เพิ่มตรงนี้
        dashboard_mode()
    elif choice == "Admin Management":
        admin_management()
    else:
        st.write("เลือกโหมดในเมนูด้านซ้าย")

if __name__ == "__main__":
    main()
