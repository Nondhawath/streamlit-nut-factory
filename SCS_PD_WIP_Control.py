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

# Dropdown สำหรับเลือกโหมด
mode = st.selectbox('Select Mode', [
    'Forming Mode (FM)', 'Tapping Receive Mode (TP)', 'Tapping Work Mode',
    'Final Inspection Receive Mode (FI)', 'Final Work Mode (FI Work)', 'TP Transfer Mode', 'Completed Mode (WH)'
])

# ฟอร์มการส่งงาน (Forming Mode)
if mode == 'Forming Mode (FM)':
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
elif mode == 'Tapping Receive Mode (TP)':
    with st.form(key='receive_work_form'):
        st.subheader('Receive Work in Tapping (TP)')
        woc_number_receive = st.text_input('Enter WOC Number to Receive')
        department_to_receive = 'Tapping'  # สำหรับการรับในแผนก Tapping
        
        receive_button = st.form_submit_button('Receive Work')
        
        if receive_button:
            receive_work(woc_number_receive, department_to_receive)
            st.success(f'Work with WOC Number {woc_number_receive} has been received in Tapping!')

# ฟอร์มการทำงานในแผนก TP (Tapping Work Mode)
elif mode == 'Tapping Work Mode':
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

# ฟอร์มการรับงาน (Final Inspection Receive Mode)
elif mode == 'Final Inspection Receive Mode (FI)':
    with st.form(key='receive_final_work_form'):
        st.subheader('Receive Work in Final Inspection (FI)')
        woc_number_fi = st.text_input('Enter WOC Number to Receive')
        department_to_fi = 'Final Inspection'  # สำหรับการรับในแผนก Final Inspection
        
        receive_button_fi = st.form_submit_button('Receive Final Work')
        
        if receive_button_fi:
            receive_work(woc_number_fi, department_to_fi)
            st.success(f'Work with WOC Number {woc_number_fi} has been received in Final Inspection!')

# ฟอร์มการทำงานในแผนก FI (Final Work Mode)
elif mode == 'Final Work Mode (FI Work)':
    with st.form(key='final_work_form'):
        st.subheader('Work in Final Inspection (FI Work)')
        woc_number_fi_work = st.text_input('WOC Number for Work in Final Inspection')
        machine_name_fi = st.selectbox('Select Machine', ['FI Machine 1', 'FI Machine 2', 'FI Machine 3'])
        fi_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        start_button_fi = st.form_submit_button('Start Final Work')
        
        if start_button_fi:
            st.session_state['work_history'].loc[st.session_state['work_history']['WOC Number'] == woc_number_fi_work, 'Status'] = f'Used - {machine_name_fi}'
            st.session_state['work_history'].loc[st.session_state['work_history']['WOC Number'] == woc_number_fi_work, 'Timestamp'] = fi_timestamp
            st.success(f'Work with WOC Number {woc_number_fi_work} is in progress on {machine_name_fi}!')

# ฟอร์มการโอนงาน (TP Transfer Mode)
elif mode == 'TP Transfer Mode':
    with st.form(key='transfer_work_form'):
        st.subheader('Transfer Work (TP Transfer Mode)')
        woc_number_transfer = st.text_input('Enter WOC Number to Transfer')
        new_woc_number = st.text_input('New WOC Number')
        
        transfer_button = st.form_submit_button('Transfer Work')
        
        if transfer_button:
            st.session_state['work_history'].loc[st.session_state['work_history']['WOC Number'] == woc_number_transfer, 'WOC Number'] = new_woc_number
            st.session_state['work_history'].loc[st.session_state['work_history']['WOC Number'] == woc_number_transfer, 'Status'] = 'Transfer'
            st.success(f'Work with WOC Number {woc_number_transfer} has been transferred to {new_woc_number}!')

# ฟอร์มการทำงานในแผนก WH (Completed Mode)
elif mode == 'Completed Mode (WH)':
    with st.form(key='completed_work_form'):
        st.subheader('Work Completed (WH Mode)')
        woc_number_completed = st.text_input('WOC Number for Completed Work')
        
        completed_button = st.form_submit_button('Complete Work')
        
        if completed_button:
            st.session_state['work_history'].loc[st.session_state['work_history']['WOC Number'] == woc_number_completed, 'Status'] = 'Completed'
            st.success(f'Work with WOC Number {woc_number_completed} has been completed and stored in Warehouse!')

# แสดงประวัติการส่งงาน
show_work_history()
