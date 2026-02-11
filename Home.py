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
            - ✅ **[Bulk Archiving Tool](./Bulk_Asrchiving_Tool)**  
            Archive multiple Kobo assets in bulk.
            - ✅ **[CodeBook Generator](./CodeBook_Generator)**
            Generate a coded book version of a tool with extra details for cleaning and analysis.
            
            ---

            ### 🚀 Coming Soon
            - Bulk Persmissions Manager
            - And many more

            ---

            ### 📬 Feedback?
            Have ideas or feedback? Get in touch!
            """)

st.link_button("Send an Email", url="mailto:abraham.azar30@outlook.com")
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
