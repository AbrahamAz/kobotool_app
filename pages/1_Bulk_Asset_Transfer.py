import streamlit as st
import requests
import json
import pandas as pd



st.set_page_config(page_title="Bulk Asset Transfer", layout="wide")

st.title("🔁 Transfer Assets in Bulk")

st.markdown("""
            This tool allows you to **transfer ownership of multiple Kobo assets** (projects) from one user to another.
            You will need to enter the **API tokens** for both the sender and receiver accounts. 
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
                1. Enter the API Token of the **sender** and **receiver** users.
                2. Authenticate to fetch their usernames and validate tokens.
                3. Select the assets owned by the sender that you want to transfer.
                4. Submit the transfer request.
                5. The transfer is **automatically** accepted on the receiver's side.

                > ⚠️ Note: You will receive email notifications from KoboToolbox about the transfer - **you can ignore these**.
                """)

# -------- Session state init --------
if "sender_token" not in st.session_state:
    st.session_state.sender_token = None
if "receiver_token" not in st.session_state:
    st.session_state.receiver_token = None
if "sender_username" not in st.session_state:
    st.session_state.sender_username = None
if "receiver_username" not in st.session_state:
    st.session_state.receiver_username = None
if "sender_assets" not in st.session_state:
    st.session_state.sender_assets = None

# --- AUTH FORM ---
if ("sender_username" not in st.session_state or st.session_state.sender_username is None) and ("receiver_username" not in st.session_state or st.session_state.receiver_username is None):
    auth_box = st.empty()  # placeholder so we can clear the form immediately
    with auth_box.form(key="token_form", clear_on_submit=True):
        st.subheader("🔐 API Token")
        col1, col2 = st.columns(2)
        with col1:
            sender_token = st.text_input("Sender User Token", placeholder="Enter sender's API token", type="password")
        with col2:
            receiver_token = st.text_input("Receiver User Token", placeholder="Enter receiver's API token", type="password")
        submit_tokens = st.form_submit_button("Authenticate")

        if submit_tokens:
            # Validate Sender
            headers_sender = {"Authorization": f"Token {sender_token}"}
            sender_resp = requests.get(f"{CONFIG['API_ROOT']}/access-logs/me/?format=json&limit=1", headers=headers_sender)
        
            # Validate Receiver
            headers_receiver = {"Authorization": f"Token {receiver_token}"}
            receiver_resp = requests.get(f"{CONFIG['API_ROOT']}/access-logs/me/?format=json&limit=1", headers=headers_receiver)


            if sender_resp.status_code == 200 and receiver_resp.status_code == 200:
                st.session_state.sender_token = sender_token
                st.session_state.receiver_token = receiver_token
                st.session_state.sender_username = sender_resp.json()['results'][0]['username']
                st.session_state.receiver_username = receiver_resp.json()['results'][0]['username']
                auth_box.empty()
                st.rerun()
            else:
                st.error("❌ Invalid token. Please try again.")

# ------ MAIN INTERFACE -------

if st.session_state.sender_username and st.session_state.receiver_username:
    st.subheader("✅ Authenticated Users")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**👤 Sender Username**")
        st.info(st.session_state.sender_username)
    with col2:
        st.markdown("**👤 Receiver Username**")
        st.info(st.session_state.receiver_username)
    
        # ------ FETCH SENDER'S ASSETS (once, with progress) ------
    headers_sender = {"Authorization": f"Token {st.session_state.sender_token}"}

    # Button to explicitly refresh data if needed
    refresh = st.button("🔄 Refresh assets list")

    if "df_assets" not in st.session_state or refresh:
        # First, get count cheaply (limit=1 keeps payload tiny)
        count_resp = requests.get(f"{CONFIG['API_ROOT']}/assets/?format=json&limit=1", headers=headers_sender)
        if count_resp.status_code != 200:
            st.error("❌ Failed to fetch sender's assets count.")
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
                    headers=headers_sender
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

    sender_assets = df_assets[
        (df_assets["name"] != "") &
        (df_assets["owner_username"] == st.session_state.sender_username)
    ]

    if not sender_assets.empty:
        # Filter UI: these won’t trigger the heavy fetch anymore
        status = st.selectbox(
            "🏴 Filter by deployment status [deployed/draft/archived]",
            options=sorted(sender_assets["deployment_status"].dropna().unique().tolist()),
            placeholder="deployed"
        )

        filtered = sender_assets[sender_assets["deployment_status"] == status]

        selected_names = st.multiselect(
            "📦 Select assets to transfer:",
            options=filtered["name"].tolist()
        )

        selected_uids = filtered[filtered["name"].isin(selected_names)]["uid"].tolist()

        if selected_uids:
            if st.button("🚀 Transfer Selected Assets"):
                recipient_url = f"{CONFIG['API_ROOT']}/users/{st.session_state.receiver_username}/"
                payload = {"recipient": recipient_url, "assets": selected_uids}
                transfer_request = requests.post(
                    f"{CONFIG['API_ROOT']}/project-ownership/invites/?format=json",
                    headers=headers_sender,
                    json=payload
                )
                if transfer_request.status_code == 201:
                    st.success("✅ Ownership transfer initiated. Awaiting receiver's auto-acceptance...")
                    invite_url = transfer_request.json().get('url')
                    patch_payload = {"status": "accepted"}
                    headers_receiver = {"Authorization": f"Token {st.session_state.receiver_token}"}
                    patch_resp = requests.patch(invite_url, headers=headers_receiver, json=patch_payload)
                    if patch_resp.status_code == 200:
                        st.success("🎉 Ownership transfer completed successfully!")
                        st.info("Note: You may receive confirmation emails from KoboToolbox. You can safely ignore them.")
                    else:
                        st.error("⚠️ Auto-accept failed.")
                        st.error(f"{patch_resp.status_code} - {patch_resp.reason}")
                else:
                    st.error("❌ Transfer request failed.")
                    st.error(f"{transfer_request.status_code} - {transfer_request.reason}")
        else:
            st.warning("⚠️ Please select at least one asset to transfer.")
    else:
        st.warning("⚠️ No assets found for this user.")

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
