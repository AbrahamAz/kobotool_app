import streamlit as st

st.set_page_config(page_title="DRC KoboTool Utility App",
                   page_icon="🛠️",
                   layout = "centered")

st.title("🛠️ KoboToolBox Utility Hub")
st.markdown("Welcome to the **KoboToolbox Utility Hub** for DRC!")

st.markdown("""
            This internal tool is designed to help streamline your Kobo workflows by providing easy-to-use interfaces for common admin tasks.

            ### 🔧 Available Tools
            Below is the list of tools you can use - more will be added soon!

            - ✅ **[Bulk Asset Transfer](./Bulk_Asset_Transfer)**  
            Transfer multiple Kobo assets from one account to another with just a few clicks.

            ---

            ### 🚀 Coming Soon
            - Bulk Persmissions Manager
            - XLS to Label Switcher
            - And many more

            ---

            ### 📬 Feedback?
            Have ideas or feedback? Get in touch with the Kobo Core Team!
            """)

st.link_button("Send an Email", url="mailto:kobo.server@drc.ngo")