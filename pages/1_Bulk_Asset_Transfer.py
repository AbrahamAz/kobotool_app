import streamlit as st
import requests
import json
import pandas as pd

CONFIG = {
    "API_ROOT": "https://kobo.drc.ngo/api/v2"
}

st.set_page_config(page_title="Bulk Asset Transfer", layout="wide")

st.title("🔁 Transfer Assets in Bulk")

st.markdown("""
            This tool allows you to **transfer ownership of multiple Kobo assets** (projects) from one user to another.
            You will need to enter the **API tokens** for both the sender and receiver accounts. 
            """)

with st.expander("ℹ️ How it works"):
    st.markdown("""
                1. Enter the API Token of the **sender** and **receiver** users.
                2. Authenticate to fetch their usernames and validate tokens.
                3. Select the assets owned by the sender that you want to transfer.
                4. Submit the transfer request.
                5. The transfer is **automatically** accepted on the receiver's side.

                > ⚠️ Note: You will receive email notifications from KoboToolbox about the transger - **you can ignore these**.
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
    

    # ------ FETCH SENDER'S ASSETS
    headers_sender = {"Authorization": f"Token {st.session_state.sender_token}"}
    asset_resp = requests.get(f"{CONFIG['API_ROOT']}/assets/?format=json", headers=headers_sender)
    if asset_resp.status_code == 200:
        assets_data = asset_resp.json()['results']
        df_assets = pd.DataFrame([
            {"uid": asset["uid"], "name": asset["name"], "owner_username": asset["owner__username"], "deployment_status": asset["deployment_status"]}
            for asset in assets_data
        ])
        sender_assets = df_assets[(df_assets["name"] != "") & (df_assets["owner_username"] == st.session_state.sender_username)]
        if not sender_assets.empty:
            status = st.selectbox(
                "🏴󠁧󠁢󠁮󠁩󠁲󠁿 Filter by deployment status [deployed/draft/archived]",
                options=sender_assets["deployment_status"].unique().tolist(),
                placeholder="deployed"
            )
            selected_names = st.multiselect(
                "📦 Select assets to transfer:",
                options=sender_assets[sender_assets["deployment_status"]== status]["name"].tolist()
            )
            selected_uids = sender_assets[sender_assets["name"].isin(selected_names)]["uid"].tolist()
            if selected_uids:
                if st.button("🚀 Transfer Selected Assets"):
                    # Prepare payload
                    recipient_url = f"{CONFIG['API_ROOT']}/users/{st.session_state.receiver_username}/"
                    payload = {
                        "recipient": recipient_url,
                        "assets": selected_uids
                    }
                    transfer_request = requests.post(
                        f"{CONFIG['API_ROOT']}/project-ownership/invites/?format=json",
                        headers=headers_sender,
                        json=payload
                    )
                    if transfer_request.status_code == 201:
                        st.success("✅ Ownership transfer initiated. Awaiting receiver's auto-acceptance...")
                        # Auto-accept with receiver
                        invite_url = transfer_request.json()['url']
                        patch_payload = {"status":"accepted"}
                        headers_receiver = {"Authorization": f"Token {st.session_state.receiver_token}"}
                        patch_resp = requests.patch(
                            invite_url,
                            headers=headers_receiver,
                            json=patch_payload
                        )
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
    else:
        st.error("❌ Failed to fetch sender's assets.")
