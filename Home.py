import streamlit as st

st.markdown(
    """
    <style>
    .css-1jc7ptx, .e1ewe7hr3, .viewerBadge_container__1QSob,
    .styles_viewerBadge__1yB5_, .viewerBadge_link__1S137,
    .viewerBadge_text__1JaDK {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)

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
            - ✅ **[XML to Label Switcher](./XML_to_Label_Switcher)**
            Switch XML variable names to Label form (more human-readable)
            - ✅ **[Bulk PII Information Switcher](./Bulk_PII_Info_Switcher)**
            Switch personal identifiable info of multiple projects.
            
            ---

            ### 🚀 Coming Soon
            - Bulk Persmissions Manager
            - And many more

            ---

            ### 📬 Feedback?
            Have ideas or feedback? Get in touch with the Kobo Core Team!
            """)

st.link_button("Send an Email", url="mailto:kobo.server@drc.ngo")