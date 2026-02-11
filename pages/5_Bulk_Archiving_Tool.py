import streamlit as st
import requests
import time
import pandas as pd



st.set_page_config(page_title="Bulk Asset Transfer", layout="wide")

st.title("🔁 Archive Assets in Bulk")

st.markdown("""
            This tool allows you to **archive kobo projects in bulk**.
            You will need to enter the **API tokens** for the owner of the assets. 
            """)

if "kobo_url" not in st.session_state:
    st.session_state.kobo_url = None

kobo_url = st.sidebar.text_input("Please enter the kobo url", value = "https://kobo.drc.ngo")
st.session_state.kobo_url = kobo_url

CONFIG = {
    "API_ROOT": f"{st.session_state.kobo_url}/api/v2"
}
with st.expander("ℹ️ How it works"):
    st.markdown("""
                1. Enter the API Token of the **owner** user.
                2. Authenticate to fetch the username and validate token.
                3. Select the assets owned by the owner that you want to archive.
                4. Submit the archiving request.
                """)

# -------- Session state init --------
if "owner_token" not in st.session_state:
    st.session_state.owner_token = None
if "owner_username" not in st.session_state:
    st.session_state.owner_username = None
if "owner_assets" not in st.session_state:
    st.session_state.owner_assets = None

# --- AUTH FORM ---
if ("owner_username" not in st.session_state or st.session_state.owner_username is None):
    auth_box = st.empty()  # placeholder so we can clear the form immediately
    with auth_box.form(key="token_form", clear_on_submit=True):
        st.subheader("🔐 API Token")
        owner_token = st.text_input("Owner User Token", placeholder="Enter owner's API token", type="password")
        submit_tokens = st.form_submit_button("Authenticate")

        if submit_tokens:
            # Validate owner
            headers_owner = {"Authorization": f"Token {owner_token}"}
            owner_resp = requests.get(f"{CONFIG['API_ROOT']}/access-logs/me/?format=json&limit=1", headers=headers_owner)


            if owner_resp.status_code == 200:
                st.session_state.owner_token = owner_token
                st.session_state.owner_username = owner_resp.json()['results'][0]['username']
                auth_box.empty()
                st.rerun()
            else:
                st.error("❌ Invalid token. Please try again.")

# ------ MAIN INTERFACE -------

if st.session_state.owner_username:
    st.subheader("✅ Authenticated User")
    st.markdown("**👤 owner Username**")
    st.info(st.session_state.owner_username)
    
        # ------ FETCH owner'S ASSETS (once, with progress) ------
    headers_owner = {"Authorization": f"Token {st.session_state.owner_token}"}

    # Button to explicitly refresh data if needed
    refresh = st.button("🔄 Refresh assets list")

    if "df_assets" not in st.session_state or refresh:
        # First, get count cheaply (limit=1 keeps payload tiny)
        count_resp = requests.get(f"{CONFIG['API_ROOT']}/assets/?format=json&limit=1", headers=headers_owner)
        if count_resp.status_code != 200:
            st.error("❌ Failed to fetch owner's assets count.")
            st.stop()

        assets_count = count_resp.json().get("count", 0)
        if assets_count == 0:
            st.session_state.df_assets = pd.DataFrame(
                columns=["uid", "name", "owner_username", "deployment_status"]
            )
        else:
            PAGE_SIZE = 100
            frames = []

            prog = st.progress(0, text=f"Fetching assets 0/{assets_count}…")
            fetched = 0

            for offset in range(0, assets_count, PAGE_SIZE):
                asset_resp = requests.get(
                    f"{CONFIG['API_ROOT']}/assets/?format=json&limit={PAGE_SIZE}&offset={offset}",
                    headers=headers_owner
                )
                if asset_resp.status_code != 200:
                    prog.empty()
                    st.error(f"❌ Failed at offset {offset}: {asset_resp.status_code} - {asset_resp.reason}")
                    st.stop()

                assets_page = asset_resp.json().get("results", [])
                df_page = pd.DataFrame([
                    {
                        "uid": a.get("uid"),
                        "name": a.get("name"),
                        "owner_username": a.get("owner__username"),
                        "deployment_status": a.get("deployment_status"),
                    }
                    for a in assets_page
                ])
                frames.append(df_page)

                # update progress by items fetched (safer than inferring from offsets)
                fetched += len(assets_page)
                prog.progress(min(fetched / max(assets_count, 1), 1.0),
                              text=f"Fetching assets {min(fetched, assets_count)}/{assets_count}…")

            prog.empty()
            st.session_state.df_assets = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
                columns=["uid", "name", "owner_username", "deployment_status"]
            )

    # From here on, just reuse the cached DataFrame — no re-fetch on widget changes
    df_assets = st.session_state.df_assets

    owner_assets = df_assets[
        (df_assets["name"] != "") &
        (df_assets["owner_username"] == st.session_state.owner_username) &
        (df_assets["deployment_status"] == "deployed")
    ]

    if not owner_assets.empty:
        selected_names = st.multiselect(
            "📦 Select assets to transfer:",
            options=owner_assets["name"].tolist()
        )

        selected_uids = owner_assets[owner_assets["name"].isin(selected_names)]["uid"].tolist()

        if selected_uids:
            if st.button("🚀 Archive Selected Assets"):
                total = len(selected_uids)
                success_count = 0
                progress_bar = st.progress(0, text="Initializing archiving...")

                for uid in selected_uids:
                    url = f"{CONFIG['API_ROOT']}/assets/{uid}/deployment/?format=json"
                    payload = {"active": "false"}
                    archiving_request = requests.patch(
                        url,
                        headers=headers_owner,
                        json=payload
                    )
                    if archiving_request.status_code == 200:
                        success_count += 1
                    else:
                        st.error(f"❌ Failed UID {uid}: {archiving_request.status_code}")

                    progress_bar.progress(success_count/total, text=f"{success_count}/{total} archived...")
                    time.sleep(0.05)

                st.success("🎉 All selected assets where successfully archived!")

            
        else:
            st.warning("⚠️ Please select at least one asset to transfer.")
    else:
        st.warning("⚠️ No deployed assets found for this user.")

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
