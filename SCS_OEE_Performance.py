import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import altair as alt

# ===== เชื่อม Google Sheets =====
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(credentials)
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1gIBZmGn86zzJWECO7Kzy5c0ibOdN1N_3Ys58M80b0kk")

# ===== กะและช่วงพัก =====
shifts = {
    "เช้า": {"start": "07:45", "end": "16:45", "breaks": [("10:00", "10:10"), ("12:00", "13:00"), ("15:00", "15:10")]},
    "OT": {"start": "17:45", "end": "19:45", "breaks": [("16:45", "17:15")]},
    "ดึก": {"start": "19:45", "end": "04:45", "breaks": [("22:00", "22:10"), ("00:00", "01:00"), ("03:00", "03:10")]}
}

def subtract_breaks(start_dt, end_dt, breaks):
    total = end_dt - start_dt
    for b_start, b_end in breaks:
        b_s = datetime.combine(start_dt.date(), datetime.strptime(b_start, "%H:%M").time())
        b_e = datetime.combine(start_dt.date(), datetime.strptime(b_end, "%H:%M").time())
        if b_s < end_dt and b_e > start_dt:
            total -= min(b_e, end_dt) - max(b_s, start_dt)
    return total

def get_next_shift_time(current, shift_name):
    shift_start = datetime.combine(current.date(), datetime.strptime(shifts[shift_name]["start"], "%H:%M").time())
    if shift_name == "ดึก" and current.time() > shift_start.time():
        shift_start += timedelta(days=1)
    return shift_start

def schedule_jobs(df, master_df):
    schedule, tracker = [], {}
    for _, row in df.iterrows():
        key = (row["AssignedMachine"], row["AssignedDate"], row["AssignedShift"])
        std = master_df.loc[master_df["ProductCode"] == row["ProductCode"], "StdTimePerPiece_min"]
        if std.empty: continue
        total_min = (row["Qty"] * std.values[0]) + 10
        date_obj = pd.to_datetime(row["AssignedDate"])
        s_info = shifts[row["AssignedShift"]]
        s_start = datetime.combine(date_obj.date(), datetime.strptime(s_info["start"], "%H:%M").time())
        s_end = datetime.combine(date_obj.date(), datetime.strptime(s_info["end"], "%H:%M").time())
        if row["AssignedShift"] == "ดึก" and s_end <= s_start: s_end += timedelta(days=1)
        now = tracker.get(key, s_start)

        while True:
            end_time = now + timedelta(minutes=total_min)
            usable = subtract_breaks(now, end_time, s_info["breaks"])
            if now + usable <= s_end:
                schedule.append({**row, "StartTime": now.strftime("%Y-%m-%d %H:%M"), "EndTime": (now + usable).strftime("%Y-%m-%d %H:%M"), "PlannedMinutes": usable.total_seconds()/60})
                tracker[key] = now + usable
                break
            else:
                if row["AssignedShift"] == "เช้า": row["AssignedShift"] = "OT"
                elif row["AssignedShift"] == "OT": row["AssignedShift"] = "ดึก"
                else:
                    row["AssignedDate"] = (date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
                    row["AssignedShift"] = "เช้า"
                key = (row["AssignedMachine"], row["AssignedDate"], row["AssignedShift"])
                now = get_next_shift_time(now, row["AssignedShift"])
                date_obj = pd.to_datetime(row["AssignedDate"])
    return pd.DataFrame(schedule)

# ===== UI หลัก =====
st.set_page_config(layout="wide")
st.title("🏭 SCS OEE Performance System")

tab1, tab2, tab3, tab4 = st.tabs(["📥 Upload & Assign", "⏱️ Schedule Plan", "📝 Log OEE", "📊 Dashboard Plan vs Actual"])

# ===== TAB 1: Upload & Assign =====
with tab1:
    upload_file = st.file_uploader("📤 อัปโหลดแผน (WO, ProductCode, Qty, Priority)", type=["xlsx"])
    if upload_file:
        plan_df = pd.read_excel(upload_file)
        if {"WO", "ProductCode", "Qty", "Priority"}.issubset(plan_df.columns):
            st.success("✅ แผนโหลดสำเร็จ กรุณา Assign เครื่อง")
            for i in range(len(plan_df)):
                col1, col2, col3 = st.columns(3)
                plan_df.loc[i, "AssignedMachine"] = col1.text_input(f"เครื่อง WO {plan_df.loc[i, 'WO']}", key=f"m{i}")
                plan_df.loc[i, "AssignedDate"] = col2.date_input(f"วันที่ WO {plan_df.loc[i, 'WO']}", key=f"d{i}")
                plan_df.loc[i, "AssignedShift"] = col3.selectbox(f"กะ WO {plan_df.loc[i, 'WO']}", ["เช้า", "OT", "ดึก"], key=f"s{i}")
            st.dataframe(plan_df)
            st.session_state["assigned_plan"] = plan_df

# ===== TAB 2: Schedule Plan =====
with tab2:
    if "assigned_plan" in st.session_state:
        product_master = pd.DataFrame(sheet.worksheet("ProductMaster").get_all_records())
        if st.button("⚙️ คำนวณและบันทึกแผน"):
            scheduled_df = schedule_jobs(st.session_state["assigned_plan"], product_master)
            st.dataframe(scheduled_df)
            sheet.values_clear("PlanSchedule!A1:Z1000")
            sheet.worksheet("PlanSchedule").update([scheduled_df.columns.tolist()] + scheduled_df.values.tolist())
            st.success("✅ บันทึกแผนลง Google Sheets แล้ว")

# ===== TAB 3: Log OEE =====
with tab3:
    oee_sheet = sheet.worksheet("OEE_Log")
    with st.form("log_oee"):
        col1, col2 = st.columns(2)
        with col1:
            log_date = st.date_input("วันที่")
            shift = st.selectbox("กะ", ["เช้า", "OT", "ดึก"])
            machine = st.text_input("เครื่องจักร")
        with col2:
            emp = st.text_input("พนักงาน")
            runtime = st.number_input("Runtime", min_value=0)
            downtime = st.number_input("Downtime", min_value=0)
            defects = st.number_input("Defects", min_value=0)
            total = st.number_input("Total Produced", min_value=0)
        if st.form_submit_button("✅ บันทึก"):
            oee_sheet.append_row([str(log_date), shift, machine, emp, runtime, downtime, defects, total])
            st.success("บันทึกแล้ว")

# ===== TAB 4: Dashboard =====
with tab4:
    plan_df = pd.DataFrame(sheet.worksheet("PlanSchedule").get_all_records())
    oee_df = pd.DataFrame(sheet.worksheet("OEE_Log").get_all_records())
    oee_df[["Runtime", "Downtime", "Defects", "TotalProduced"]] = oee_df[["Runtime", "Downtime", "Defects", "TotalProduced"]].apply(pd.to_numeric, errors="coerce").fillna(0)
    merged = pd.merge(plan_df, oee_df, left_on=["AssignedMachine", "AssignedDate", "AssignedShift"], right_on=["MachineID", "Date", "Shift"], how="left")
    merged["ActualQty"] = merged["TotalProduced"]
    merged["ActualMin"] = merged["Runtime"]
    merged["Ach%"] = (merged["ActualQty"] / merged["Qty"]) * 100
    merged["AchTime%"] = (merged["ActualMin"] / merged["PlannedMinutes"]) * 100
    st.dataframe(merged[["WO", "AssignedMachine", "AssignedDate", "AssignedShift", "Qty", "ActualQty", "Ach%", "PlannedMinutes", "ActualMin", "AchTime%"]])
    chart = alt.Chart(merged).mark_bar().encode(
        x="WO:N",
        y="Ach%",
        color=alt.condition(alt.datum.Ach% >= 100, alt.value("green"), alt.value("red")),
        tooltip=["WO", "Qty", "ActualQty", "Ach%"]
    ).properties(width=800, height=400)
    st.altair_chart(chart, use_container_width=True)
