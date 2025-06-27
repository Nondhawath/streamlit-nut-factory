import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Google Sheets setup
google_credentials = st.secrets["google_service_account"]  # Get Google credentials directly from secrets

# Define the scope for Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Authorize the credentials and set up the client
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_credentials, scope)
client = gspread.authorize(creds)

# Spreadsheet ID (Replace with your actual Spreadsheet ID)
spreadsheet_id = '1GbHXO0d2GNXEwEZfeygGqNEBRQJQUoC_MO1mA-389gE'  # Replace this with your actual Spreadsheet ID

# Function to cache data from Google Sheets
@st.cache_data
def get_sheet_data(sheet_name):
    sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
    return sheet.get_all_records()

# Use the cached data
part_code_master_data = get_sheet_data('part_code_master')

# Display Part Code Master Data
def display_part_code_master_data():
    # Debugging: Display the part_code_master_data to check its structure
    st.write("Part Code Master Data (for debugging):")
    st.write(part_code_master_data)

    part_codes = [part['รหัสงาน'] for part in part_code_master_data if 'รหัสงาน' in part]
    
    if part_codes:
        part_codes.sort()
        ranges = []
        # Create ranges based on the sorted part codes
        for i in range(0, len(part_codes), 100):
            start = part_codes[i]
            end = part_codes[i + 99] if i + 99 < len(part_codes) else part_codes[-1]
            ranges.append(f"[{start} - {end}]")

        # Display the Part Code Ranges
        st.write("Part Code Master Data Ranges:")
        st.write(ranges)
    
    # Check for 'Part Name' in part_code_master_data
    if 'Part Name' in part_code_master_data[0]:
        part_names = [part['Part Name'] for part in part_code_master_data if 'Part Name' in part and part['Part Name']]
        if part_names:
            st.write("Part Names:")
            st.write(part_names)
        else:
            st.write("No Part Names found.")
    else:
        st.write("Error: 'Part Name' column not found in part_code_master_data!")

# Call the function to display the data
display_part_code_master_data()

# Google Sheets data to save work statuses and timestamps
def add_status_timestamp(row_data, status_column_index, status_value):
    timestamp = datetime.now().strftime('%d-%m-%Y %H:%M')  # Format: 26-06-2025 14:54
    row_data[status_column_index] = status_value  # Set the status
    row_data[status_column_index + 1] = timestamp  # Add timestamp next to the status
    return row_data

# Forming Mode
def forming_mode():
    st.header("Forming Mode")
    department_from = st.selectbox('เลือกแผนกต้นทาง', ['Forming', 'Tapping', 'Final'])
    department_to = st.selectbox('เลือกแผนกปลายทาง', ['Forming', 'Tapping', 'Final'])
    woc_number = st.text_input("หมายเลข WOC")
    
    # Make sure to load the 'Part Name' correctly
    part_name = st.selectbox("รหัสงาน / Part Name", [part['Part Name'] for part in part_code_master_data if 'Part Name' in part])
    
    lot_number = st.text_input("หมายเลข LOT")
    total_weight = st.number_input("น้ำหนักรวม", min_value=0.0)
    barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0)
    sample_weight = st.number_input("น้ำหนักรวมของตัวอย่าง", min_value=0.0)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=1)

    # Calculate number of pieces
    if total_weight and barrel_weight and sample_weight and sample_count:
        pieces_count = (total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000)
        st.write(f"จำนวนชิ้นงาน: {pieces_count:.2f}")
    
    if st.button("บันทึก"):
        # Save data to Google Sheets with timestamp
        row_data = [department_from, department_to, woc_number, part_name, lot_number, total_weight, barrel_weight, sample_weight, sample_count, pieces_count]
        row_data = add_status_timestamp(row_data, 11, "WIP-Forming")  # Add timestamp to the row
        sheet = client.open_by_key(spreadsheet_id).worksheet('Jobs')
        sheet.append_row(row_data)  # Save the row to "Jobs" sheet
        st.success("บันทึกข้อมูลสำเร็จ!")

# Main app logic
def main():
    st.title("ระบบรับส่งงานระหว่างแผนกในโรงงาน")
    mode = st.sidebar.selectbox("เลือกโหมด", ['Forming', 'Tapping', 'Final Inspection', 'Final Work', 'TP Transfer'])

    if mode == 'Forming':
        forming_mode()
    # Add more modes if necessary (Final Inspection, Final Work, etc.)

if __name__ == "__main__":
    main()
