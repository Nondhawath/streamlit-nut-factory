import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st

# Define the scope for Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Function to get Google Sheets client and handle exceptions
def get_google_sheets_client():
    try:
        google_credentials = st.secrets["google_service_account"]  # Get Google credentials directly from secrets
        creds = ServiceAccountCredentials.from_json_keyfile_dict(google_credentials, scope)
        client = gspread.authorize(creds)
        return client
    except gspread.exceptions.APIError as e:
        st.error(f"API Error while accessing Google Sheets: {e}")
        return None
    except gspread.exceptions.SpreadsheetNotFound as e:
        st.error(f"Spreadsheet not found: {e}")
        return None
    except gspread.exceptions.GSpreadException as e:
        st.error(f"GSpreadException: {e}")
        return None
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return None

# Function to open specific sheets and handle exceptions
def open_sheets():
    client = get_google_sheets_client()
    if client is None:
        return None, None, None, None
    try:
        sheet = client.open_by_key('1GbHXO0d2GNXEwEZfeygGqNEBRQJQUoC_MO1mA-389gE').worksheet('Jobs')  # "Jobs" sheet
        part_code_master_sheet = client.open_by_key('1GbHXO0d2GNXEwEZfeygGqNEBRQJQUoC_MO1mA-389gE').worksheet('part_code_master')
        employees_sheet = client.open_by_key('1GbHXO0d2GNXEwEZfeygGqNEBRQJQUoC_MO1mA-389gE').worksheet('Employees')
        transfer_logs_sheet = client.open_by_key('1GbHXO0d2GNXEwEZfeygGqNEBRQJQUoC_MO1mA-389gE').worksheet('Transfer Logs')
        return sheet, part_code_master_sheet, employees_sheet, transfer_logs_sheet
    except gspread.exceptions.GSpreadException as e:
        st.error(f"Error while accessing one of the sheets: {e}")
        return None, None, None, None
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return None, None, None, None

# Check if sheet connection is successful
def check_sheet_connection():
    sheet, part_code_master_sheet, employees_sheet, transfer_logs_sheet = open_sheets()
    if sheet and part_code_master_sheet:
        st.success("เชื่อมต่อกับ Google Sheets สำเร็จ!")
    else:
        st.error("ไม่สามารถเชื่อมต่อกับ Google Sheets ได้!")

# Main app logic
def main():
    st.title("ระบบรับส่งงานระหว่างแผนกในโรงงาน")
    
    # Test connection to Google Sheets
    check_sheet_connection()

    # Select mode (Forming, Tapping, etc.)
    mode = st.selectbox("เลือกโหมดการทำงาน", ['Forming', 'Tapping', 'Final Inspection', 'Final Work', 'TP Transfer'])

    sheet, part_code_master_sheet, employees_sheet, transfer_logs_sheet = open_sheets()  # Open sheets

    if sheet:  # Check if the sheets were successfully opened
        if mode == 'Forming':
            forming_mode(sheet, part_code_master_sheet)
        elif mode == 'Tapping':
            tapping_mode(sheet)
        elif mode == 'Final Inspection':
            pass
        elif mode == 'Final Work':
            pass
        elif mode == 'TP Transfer':
            pass
    else:
        st.error("ไม่สามารถเชื่อมต่อกับ Google Sheets ได้!")

if __name__ == "__main__":
    main()
