import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime
import requests

# ฟังก์ชันเชื่อมต่อฐานข้อมูล PostgreSQL
def get_connection():
    conn_str = st.secrets["postgres"]["conn_str"]
    conn = psycopg2.connect(conn_str)
    return conn

# ฟังก์ชันส่งข้อความ Telegram
TELEGRAM_TOKEN = st.secrets["telegram"]["token"]
CHAT_ID = st.secrets["telegram"]["chat_id"]

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    requests.get(url)

# ฟังก์ชันเพิ่ม timestamp ในข้อมูล
def add_timestamp(data_dict):
    data_dict['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return data_dict

# ฟังก์ชันดึงข้อมูลจากตาราง (อ่านทั้งหมด)
@st.cache_data(ttl=60)
def get_data(table_name):
    conn = get_connection()
    query = f"SELECT * FROM {table_name};"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# ฟังก์ชันเพิ่มข้อมูลใหม่ลงในตาราง
def insert_data(table_name, data_dict):
    conn = get_connection()
    cursor = conn.cursor()

    # เตรียมคำสั่ง SQL แบบ dynamic
    columns = ', '.join(data_dict.keys())
    placeholders = ', '.join(['%s'] * len(data_dict))
    values = list(data_dict.values())

    sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
    cursor.execute(sql, values)
    conn.commit()
    cursor.close()
    conn.close()

# ฟังก์ชันอัพเดตสถานะในตาราง
def update_status(table_name, woc_number, new_status):
    conn = get_connection()
    cursor = conn.cursor()
    sql = f"UPDATE {table_name} SET status = %s WHERE woc_number = %s"
    cursor.execute(sql, (new_status, woc_number))
    conn.commit()
    cursor.close()
    conn.close()

# -------------- โหมด Forming ----------------
def forming_mode():
    st.header("Forming Mode (FM)")
    department_from = "FM"
    department_to = st.selectbox('แผนกปลายทาง', ['TP', 'FI', 'OS'])
    woc_number = st.text_input("หมายเลข WOC")

    # ดึงรหัสงานจากตาราง part_code_master
    part_codes_df = get_data("part_code_master")
    part_codes = part_codes_df['part_code'].tolist() if 'part_code' in part_codes_df.columns else []
    part_name = st.selectbox("รหัสงาน / Part Name", part_codes)

    lot_number = st.text_input("หมายเลข LOT")
    total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
    barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
    sample_weight = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1, step=1)

    pieces_count = None
    if total_weight and barrel_weight and sample_weight and sample_count > 0:
        try:
            pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)
            st.write(f"จำนวนชิ้นงาน: {pieces_count:.2f}")
        except ZeroDivisionError:
            st.error("จำนวนตัวอย่างต้องไม่เป็นศูนย์")

    if st.button("บันทึก"):
        if all([woc_number, part_name, lot_number, pieces_count]):
            row_data = {
                'woc_number': woc_number,
                'part_name': part_name,
                'operator': "นายคมสันต์",
                'department_from': department_from,
                'department_to': department_to,
                'lot_number': lot_number,
                'total_weight': total_weight,
                'barrel_weight': barrel_weight,
                'sample_weight': sample_weight,
                'sample_count': sample_count,
                'pieces_count': pieces_count,
                'status': "WIP-Forming"
            }
            row_data = add_timestamp(row_data)
            insert_data("fm_table", row_data)
            st.success("บันทึกข้อมูลสำเร็จ!")
            send_telegram_message(f"Forming ส่งงานหมายเลข WOC {woc_number} ไปยัง {department_to}")
        else:
            st.warning("กรุณากรอกข้อมูลให้ครบถ้วน")

# -------------- โหมด Tapping Receive ----------------
def tapping_receive_mode():
    st.header("Tapping Receive Mode (TP)")
    department_from = "FM"
    department_to = "TP"

    # ดึงข้อมูลจาก fm_table ที่ status = 'WIP-Forming'
    fm_df = get_data("fm_table")
    wip_df = fm_df[fm_df['status'] == 'WIP-Forming']
    woc_list = wip_df['woc_number'].tolist()

    woc_number = st.selectbox("เลือกหมายเลข WOC", woc_list)
    if woc_number:
        selected_job = wip_df[wip_df['woc_number'] == woc_number].iloc[0]

        st.write(f"Part Name: {selected_job['part_name']}")
        st.write(f"Lot Number: {selected_job['lot_number']}")
        st.write(f"Total Weight: {selected_job['total_weight']}")
        st.write(f"Barrel Weight: {selected_job['barrel_weight']}")
        st.write(f"Sample Weight: {selected_job['sample_weight']}")
        st.write(f"Sample Count: {selected_job['sample_count']}")
        st.write(f"Pieces Count: {selected_job['pieces_count']:.2f}")

    if st.button("รับงาน"):
        if woc_number:
            update_status("fm_table", woc_number, "Tapping-Received")
            st.success(f"รับงานหมายเลข {woc_number} สำเร็จ!")
            send_telegram_message(f"Tapping รับงานหมายเลข WOC {woc_number}")
        else:
            st.warning("กรุณาเลือกหมายเลข WOC")

# -------------- โหมด Final Inspection Receive ----------------
def final_inspection_receive_mode():
    st.header("Final Inspection Receive Mode (FI)")
    department_from = "TP"
    department_to = "FI"

    tp_df = get_data("tp_table")
    wip_df = tp_df[tp_df['status'] == 'Tapping-Received']
    woc_list = wip_df['woc_number'].tolist()

    woc_number = st.selectbox("เลือกหมายเลข WOC", woc_list)

    total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
    barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
    sample_weight = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1, step=1)

    pieces_count = None
    if total_weight and barrel_weight and sample_weight and sample_count > 0:
        try:
            pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)
            st.write(f"จำนวนชิ้นงาน: {pieces_count:.2f}")
        except ZeroDivisionError:
            st.error("จำนวนตัวอย่างต้องไม่เป็นศูนย์")

    if st.button("รับงาน"):
        if all([woc_number, pieces_count]):
            row_data = {
                'woc_number': woc_number,
                'part_name': "AP00002",  # แก้ให้ตรงกับจริงหรือดึงจากฐานข้อมูล
                'operator': "นายคมสันต์",
                'department_from': department_from,
                'department_to': department_to,
                'lot_number': "Lot124",  # แก้ตามข้อมูลจริง
                'total_weight': total_weight,
                'barrel_weight': barrel_weight,
                'sample_weight': sample_weight,
                'sample_count': sample_count,
                'pieces_count': pieces_count,
                'status': "Final Inspection-Received"
            }
            row_data = add_timestamp(row_data)
            insert_data("fi_table", row_data)
            update_status("tp_table", woc_number, "Final Inspection-Received")
            st.success("รับงานจาก Tapping สำเร็จ!")
            send_telegram_message(f"Final Inspection รับงานหมายเลข WOC {woc_number}")
        else:
            st.warning("กรุณากรอกข้อมูลให้ครบถ้วน")

# -------------- Main ----------------
def main():
    st.title("ระบบการโอนถ่ายงานระหว่างแผนก (Supabase PostgreSQL)")

    mode = st.sidebar.selectbox("เลือกโหมด", [
        "Forming Mode",
        "Tapping Receive Mode",
        "Final Inspection Receive Mode",
    ])

    if mode == "Forming Mode":
        forming_mode()
    elif mode == "Tapping Receive Mode":
        tapping_receive_mode()
    elif mode == "Final Inspection Receive Mode":
        final_inspection_receive_mode()

if __name__ == "__main__":
    main()
