import streamlit as st
import pandas as pd
import numpy as np
import zipfile
import io
from src.utils import *



st.set_page_config(page_title="XML to Label Switcher", layout="wide")

st.title("🔁 Switch from XML to Label")

st.markdown("""
            This tool lets you switch your dataset from **XML (variable names)** to **Label format** (human-readable).  
            You need to upload both the **modified data** and the **original Kobo XLSForm**.
            """)

with st.expander("ℹ️ How it works"):
    st.markdown("""
                1. Upload the **modified dataset** and the **original Kobo XLSForm**.
                2. Select the **label language** you want to switch to.
                3. Click **Run Switch** to update both column headers and values.
                4. Preview or download the converted dataset.
                """)
    
# -------- Session state init --------
for key in ["data_excel", "form_excel", "tool_survey", "tool_choices", 
            "data_list", "label", "sep", "switch_triggered",
              "switch_complete","files_accepted", "preview_df"]:
    if key not in st.session_state:
        st.session_state[key] = None
# st.session_state.switch_triggered = False
# st.session_state.files_accepted = False

# ----- FORM UPLOAD ------
if ("data_excel" not in st.session_state or st.session_state.data_excel is None) and ("form_excel" not in st.session_state or st.session_state.form_excel is None):
    auth_box = st.empty()  # placeholder so we can clear the form immediately
    with auth_box.form(key="upload_form", clear_on_submit=True):
        st.subheader("📁 Upload Data and Form")

        col1, col2 = st.columns(2)
        with col1:
            data = st.file_uploader("Upload Modified Data File", type="xlsx")
        with col2:
            tool = st.file_uploader("Upload Kobo XLSForm", type="xlsx")
            sep = st.selectbox("Select seperator used in select_multiple column names", 
                              options=["/",".","__"])
            st.session_state.sep = sep

        submit = st.form_submit_button("Upload")


    if submit and data and tool:
        try:
            st.session_state.data_excel = pd.ExcelFile(data)
            st.session_state.form_excel = pd.ExcelFile(tool)
            st.session_state.switch_complete = False  # Reset after upload
            # Validate Receiver
            if "survey" in st.session_state.form_excel.sheet_names and "choices" in st.session_state.form_excel.sheet_names:
                auth_box.empty()
                st.session_state.files_accepted = True
                st.rerun()
            else:
                st.error("❌ Kobo form must include 'survey' and 'choices' sheets.")
        except Exception as e:
            st.error(f"❌ Failed to read Excel files: {e}")

if st.session_state.files_accepted:
    with st.container(border=True):
        st.markdown("**✅ Files loaded**")
        st.write(f"- Data sheets: {', '.join(st.session_state.data_excel.sheet_names)}")
        st.write(f"- Form sheets: {', '.join(st.session_state.form_excel.sheet_names)}")
        st.write(f"- Separator: `{st.session_state.sep}`")

# st.session_state.switch_complete = False
# st.session_state.files_accepted = True
# ----- FIXING FORM ------
if st.session_state.form_excel and st.session_state.files_accepted:
    # Add new list_name and q_type columns to tool_survey
    tool_survey = st.session_state.form_excel.parse('survey')
    tool_survey = tool_survey[tool_survey['name'].notna()].copy()
    tool_survey["q_type"] = tool_survey['type'].apply(q_type)
    tool_survey['list_name'] = tool_survey['type'].apply(list_name)
    st.session_state.tool_survey = tool_survey

    # Filter all na from list_name in tool_choice
    tool_choices = st.session_state.form_excel.parse('choices')
    tool_choices = tool_choices[tool_choices['list_name'].notna()].copy()
    st.session_state.tool_choices = tool_choices

# ----- CHOOSE LABEL ------
if st.session_state.tool_survey is not None:
    label_colname = [col for col in st.session_state.tool_survey.columns if 'label' in col]

    if len(label_colname) > 1:
        label = st.selectbox(
            "🌍 Select label language",
            options= label_colname,
        )
        if label:
            st.session_state.label = label
            st.success(f"Label column selected: `{label}`")
    elif len(label_colname) == 1:
        label = label_colname[0]
        st.session_state.label = label
        st.info(f"Only one label found. Using: `{label}`")
    else:
        st.error("❌ No label columns found in survey sheet.")
        

# ----- FIXING DATA ------
if st.session_state.data_excel and st.session_state.files_accepted:
    # Read all the data inside a data_list
    data_list = [st.session_state.data_excel.parse(sheet) for sheet in st.session_state.data_excel.sheet_names]
    st.session_state.data_list = data_list

# ----- Button to Run Switch -----
if st.session_state.label and st.session_state.data_list and st.session_state.tool_survey is not None:
    if st.button("🔁 Run Switch"):
        st.session_state.switch_triggered = True
        st.session_state.switch_complete = False
        st.session_state.preview_df = None
        st.rerun()

# ----- Apply Switch -----
if st.session_state.switch_triggered and not st.session_state.switch_complete:
    with st.spinner("Switching column headers and choice values..."):
        data_list = st.session_state.data_list
        tool_survey = st.session_state.tool_survey
        tool_choices = st.session_state.tool_choices
        label = st.session_state.label
        sep = st.session_state.sep

        tool_s_one = tool_survey[tool_survey['q_type'] == "select_one"]
        tool_s_multi = tool_survey[tool_survey['q_type'] == "select_multiple"]

        progress = st.progress(0)
        total_steps = len(data_list) * 3
        step = 0

        for i in range(len(data_list)):
            data = data_list[i]
            data_columns = data.columns

            # Remove NA columns first
            data = data.loc[:, ~data.columns.isna()]

            # Select One
            for col in tool_s_one['name']:
                if col in data.columns:
                    data[col] = name2label_choices_one(tool_survey, tool_choices, label, data, col)
            step += 1
            progress.progress(step / total_steps)

            # Select Multiple
            for col in tool_s_multi['name']:
                if col in data.columns:
                    data[col] = name2label_choices_multiple(tool_survey, tool_choices, data, col, label, sep)
            step += 1
            progress.progress(step / total_steps)

            # Rename Headers
            new_col_names = [name2label_questions(tool_survey, tool_choices, col, label, sep) for col in data.columns]
            data.columns = new_col_names
            data_list[i] = data

            step += 1
            progress.progress(step / total_steps)

        st.session_state.data_list = data_list
        prewiew = data_list[0].head().copy()
        prewiew.columns = make_unique_columns(prewiew.columns)
        st.session_state.preview_df = prewiew
        st.session_state.switch_complete = True
        st.session_state.switch_triggered = False
        
    st.success("✅ Switch complete!")

if st.session_state.preview_df is not None:
    st.subheader("👀 Preview (first sheet, first 5 rows)")
    st.dataframe(st.session_state.preview_df, use_container_width=True)

if st.session_state.switch_complete and st.session_state.data_list:
    st.subheader("📥 Download your switched dataset")

    # Download Excel
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        original_sheet_names = st.session_state.data_excel.sheet_names
        # then inside the writer:
        for idx, df in enumerate(st.session_state.data_list):
            sheet_name = original_sheet_names[idx]
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    excel_bytes = excel_buffer.getvalue()

    st.download_button(
        label="📄 Download as Excel (.xlsx)",
        data=excel_bytes,
        file_name="relabeled_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Download CSV ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for idx, df in enumerate(st.session_state.data_list):
            csv_bytes = df.to_csv(index=False).encode('utf-8')
            zipf.writestr(f"Sheet{idx + 1}.csv", csv_bytes)
    zip_bytes = zip_buffer.getvalue()

    st.download_button(
        label="🗂️ Download as CSV (.zip)",
        data=zip_bytes,
        file_name="relabeled_data.zip",
        mime="application/zip"
    )

    # Footer
st.markdown(
    """
    <style>
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #f5f5f5;
        color: #555;
        text-align: center;
        justify-contents: center;
        padding: 10px;
        font-size: 14px;
        border-top: 1px solid #ddd;
    }
    </style>
    <div class="footer">
        Made with ❤️ using Streamlit | © 2025 - Abraham Azar
    </div>
    """,
    unsafe_allow_html=True
)