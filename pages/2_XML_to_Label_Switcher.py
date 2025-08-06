import streamlit as st
import pandas as pd
import numpy as np
from src.utils import *

st.set_page_config(page_title="XML to Label Switcher", layout="wide")

st.title("🔁 Switch from XML to Label")

st.markdown("""
            This tool allows you to **switch you dataset from XLS to Labels** after doing some changes to the data.
            You will need to enter the **changed data** as well as the **Kobo Tool (XLS Form)**. 
            """)

with st.expander("ℹ️ How it works"):
    st.markdown("""
                1. Enter the **Changed Data** and the **Kobo XLS Form Tool**.
                2. Choose which **Language** from the available ones in the tool to switch to.
                3. Switch all the column headers to Labels.
                4. Switch all the values in the data to Labels.
                5. Download the data through **XLSX** or **CSV**.
                """)
    
# -------- Session state init --------
if "data_excel" not in st.session_state:
    st.session_state.data_excel = None
if "form_excel" not in st.session_state:
    st.session_state.form_excel = None
if "tool_survey" not in st.session_state:
    st.session_state.tool_survey = None
if "tool_choices" not in st.session_state:
    st.session_state.tool_choices = None
if "data_list" not in st.session_state:
    st.session_state.data_list = None
if "label" not in st.session_state:
    st.session_state.label = None

# ----- FORM UPLOAD ------
if not (st.session_state.data_excel and st.session_state.form_excel):
    with st.form(key = "upload_form"):
        st.subheader("📁 Upload Data and Form")

        col1, col2 = st.columns(2)
        with col1:
            data = st.file_uploader("Choose your Data File", type="xlsx")
        with col2:
            tool = st.file_uploader("Choose your Form File", type="xlsx")

        submit_tokens = st.form_submit_button("Authenticate")


    if submit_tokens and not(data is None or tool is None):
        data_excel = pd.ExcelFile(data)
        form_excel = pd.ExcelFile(tool)
        sheet_names_data = data_excel.sheet_names
        sheet_names_form = form_excel.sheet_names
        
        # Validate Receiver
        if "survey" in sheet_names_form and "choices" in sheet_names_form:
            st.session_state.data_excel = data_excel
            st.session_state.form_excel = form_excel
            st.success(f"✅ Form includes all survey and choices and Data includes the following sheets {sheet_names_data}")
        else:
            st.error("❌ Invalid Data and Form uploaded. Please verify and try again.")


# ----- FIXING FORM ------
if st.session_state.form_excel:
    # Add new list_name and q_type columns to tool_survey
    tool_survey = st.session_state.form_excel.parse('survey')
    tool_survey = tool_survey[tool_survey['name'].notna()].copy()
    tool_survey["q_type"] = tool_survey['type'].apply(lambda x: str(x).split()[0] if isinstance(x, str) and x.strip() else None)
    tool_survey['list_name'] = tool_survey['type'].apply(lambda x: str(x).split()[1] if isinstance(x, str) and len(str(x).split()) > 1 else None)
    st.session_state.tool_survey = tool_survey

    # Filter all na from list_name in tool_choice
    tool_choices = st.session_state.form_excel.parse('choices')
    tool_choices = tool_choices[tool_choices['list_name'].notna()].copy()
    st.session_state.tool_choices = tool_choices

# ----- CHOOSE LABEL ------
if st.session_state.form_excel:
    tool_survey = st.session_state.tool_survey
    label_colname = [col for col in tool_survey.columns if 'label' in col]

    st.markdown(label_colname)
    
    # TO ADD A SELECT LANGUAGE IN CASE MANY WAS DETECTED AND IF ONLY ONE RETURN A MESSAGE THAT SAY THIS IS THE LANGUAGE

# ----- FIXING DATA ------
if st.session_state.data_excel:
    # Read all the data inside a data_list
    data_list = []
    for i in st.session_state.data_excel.sheet_names:
        data_list.append(st.session_state.data_excel.parse(i))
    st.session_state.data_list = data_list

# ----- SWITCHING DATA -----
if st.session_state.data_list and st.session_state.tool_survey and st.session_state.tool_choices:
    # Start with Select One questions
    tool_s_one = st.session_state.tool_survey
    tool_s_one = tool_s_one[tool_s_one['q_type'] == "select_one"]

    columns_tool_s_one = tool_s_one['name']

    for data in data_list:
        for i in range(1, len(columns_tool_s_one)):
            if data[[columns_tool_s_one[i]]] is not None:
                data[[columns_tool_s_one[i]]] = name2label_choices_one(tool_survey,tool_choices,data,columns_tool_s_one[i],)
