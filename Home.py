import streamlit as st

st.set_page_config(page_title="KoboTool Utility App",
                   page_icon="🛠️",
                   layout = "centered")

st.title("🛠️ KoboToolBox Utility Hub")
st.markdown("Welcome to the **KoboToolbox Utility Hub**!")

st.markdown("""
            This internal tool is designed to help streamline your Kobo workflows by providing easy-to-use interfaces for common admin tasks.

            ### 🔧 Available Tools
            Below is the list of tools you can use - more will be added soon!

            - ✅ **[Bulk Asset Transfer](./Bulk_Asset_Transfer)**  
            Transfer multiple Kobo assets from one account to another with just a few clicks.
            - ✅ **[XML to Label Switcher](./XML_to_Label_Switcher)**
            Switch XML variable names to Label form (more human-readable)
            - ✅ **[Project Metadata Switcher](./Project_Metadata_Switcher)**
            Switch personal identifiable info, sector/function and legal entity of multiple projects.
            - ✅ **[Project Overview Dashboard](./Project_Overview)**
            Provides an overview of all projects owned by a Kobo user.
            
            ---

            ### 🚀 Coming Soon
            - Bulk Persmissions Manager
            - And many more

            ---

            ### 📬 Feedback?
            Have ideas or feedback? Get in touch with the Kobo Core Team!
            """)

st.link_button("Send an Email", url="mailto:abraham.azar30@outlook.com")