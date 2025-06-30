import streamlit as st
import pandas as pd
from datetime import datetime

# ใช้ข้อมูลแผนกที่กำหนดไว้
departments = ['Forming', 'Tapping', 'Final Inspection', 'Out Source', 'Warehouse']

# สร้าง DataFrame เพื่อเก็บข้อมูลการรับส่งงาน
if 'work_history' not in st.session_state:
    st.session_state['work_history'] = pd.DataFrame(columns=[
        'WOC Number', 'Part Name', 'Employee', 'Department From', 'Department To', 'Lot Number', 
        'Total Weight', 'Barrel Weight', 'Sample Weight', 'Sample Count', 'Pieces Count', 
        'Status', 'Timestamp'
    ])

# ฟังก์ชันคำนวณ Pieces Count
def calculate_pieces_count(total_weight, barrel_weight, sample_weight, sample_count):
    return (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)

# ฟังก์ชันส่งงาน
def send_work(woc_number, part_name, employee, department_from, department_to, lot_number, total_weight, barrel_weight, sample_weight, sample_count):
    pieces_count = calculate_pieces_count(total_weight, barrel_weight, sample_weight, sample_count)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_row = pd.DataFrame([[woc_number, part_name, employee, department_from, department_to, lot_number, 
                             total_weight, barrel_weight, sample_weight, sample_count, pieces_count, 'WIP-Forming', timestamp]],
                           columns=st.session_state['work_history'].columns)
    st.session_state['work_history'] = pd.concat([st.session_state['work_history'], new_row], ignore_index=True)

# ฟังก์ชันรับงาน
def receive_work(woc_number, department_to):
    st.session_state['work_history'].loc[st.session_state['work_history']['WOC Number'] == woc_number, 'Department To'] = department_to
    st.session_state['work_history'].loc[st.session_state['work_history']['WOC Number'] == woc_number, 'Status'] = 'Received'
    st.session_state['work_history'].loc[st.session_state['work_history']['WOC Number'] == woc_number, 'Timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ฟังก์ชันแสดงประวัติการส่งงาน
def show_work_history():
    st.subheader('Work History')
    st.dataframe(st.session_state['work_history'])

# ส่วนของฟอร์มรับส่งงาน
st.title('Work Transfer System')

# ฟอร์มการส่งงาน (Forming Mode)
with st.form(key='send_work_form'):
    st.subheader('Send Work from Forming (FM)')
    woc_number = st.text_input('WOC Number')
    part_name = st.text_input('Part Name')
    employee = st.text_input('Employee')
    department_from = 'Forming'  # แสดงว่าเริ่มจากแผนก Forming
    department_to = st.selectbox('Department To', ['Tapping', 'Final Inspection', 'Out Source'])
    lot_number = st.text_input('Lot Number')
    total_weight = st.number_input('Total Weight', min_value=0.0, step=0.1)
    barrel_weight = st.number_input('Barrel Weight', min_value=0.0, step=0.1)
    sample_weight = st.number_input('Sample Weight', min_value=0.0, step=0.1)
    sample_count = st.number_input('Sample Count', min_value=0, step=1)
    
    send_button = st.form_submit_button('Send Work')
    
    if send_button:
        send_work(woc_number, part_name, employee, department_from, department_to, lot_number, total_weight, barrel_weight, sample_weight, sample_count)
        st.success('Work has been sent!')

# ฟอร์มการรับงาน (Tapping Receive Mode)
with st.form(key='receive_work_form'):
    st.subheader('Receive Work in Tapping (TP)')
    woc_number_receive = st.text_input('Enter WOC Number to Receive')
    department_to_receive = 'Tapping'  # สำหรับการรับในแผนก Tapping
    
    receive_button = st.form_submit_button('Receive Work')
    
    if receive_button:
        receive_work(woc_number_receive, department_to_receive)
        st.success(f'Work with WOC Number {woc_number_receive} has been received in Tapping!')

# ฟอร์มการทำงานในแผนก TP (Tapping Work Mode)
with st.form(key='tapping_work_form'):
    st.subheader('Work in Tapping (TP)')
    woc_number_tp = st.text_input('WOC Number for Work in Tapping')
    machine_name = st.selectbox('Select Machine', ['TP Machine 1', 'TP Machine 2', 'TP Machine 3'])
    tapping_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    start_button = st.form_submit_button('Start Work')
    
    if start_button:
        st.session_state['work_history'].loc[st.session_state['work_history']['WOC Number'] == woc_number_tp, 'Status'] = f'Used - {machine_name}'
        st.session_state['work_history'].loc[st.session_state['work_history']['WOC Number'] == woc_number_tp, 'Timestamp'] = tapping_timestamp
        st.success(f'Work with WOC Number {woc_number_tp} is in progress on {machine_name}!')

# แสดงประวัติการส่งงาน
show_work_history()
