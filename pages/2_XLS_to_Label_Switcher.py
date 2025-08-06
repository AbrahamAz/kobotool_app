import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="XLS to Label Switcher", layout="wide")

st.title("🔁 Switch from XLS to Label")

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
    
