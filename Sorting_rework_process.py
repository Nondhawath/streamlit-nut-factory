
import streamlit as st

st.title("โรงงานคัดแยกน๊อต - Rework/Scrap")
st.write("แอปนี้ใช้สำหรับติดตามสถานะของงานในกระบวนการคัดแยก")

job_status = st.selectbox("สถานะงาน", ["Sorting", "Rework", "Oil Cleaning", "Wash/Dry", "Scrap"])
quantity = st.number_input("จำนวนงาน", min_value=0)

if st.button("บันทึก"):
    st.success(f"บันทึกแล้ว: {job_status} จำนวน {quantity} ชิ้น")
