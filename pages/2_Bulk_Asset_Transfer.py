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


# ----- FORM TOKEN ------
if not (st.session_state.sender_username and st.session_state.receiver_username):
    with st.form(key = "token_form"):
        st.subheader("🔐 API Tokens")

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
            st.success("✅ Tokens verified and users authenticated")
            st.rerun()
        else:
            st.error("❌ Invalid tokens(s). Please check both tokens and try again.")

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
            {"uid": asset["uid"], "name": asset["name"], "owner_username": asset["owner__username"]}
            for asset in assets_data
        ])
        sender_assets = df_assets[df_assets["owner_username"] == st.session_state.sender_username]
        if not sender_assets.empty:
            selected_names = st.multiselect(
                "📦 Select assets to transfer:",
                options=sender_assets["name"].tolist()
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




# col1, col2 = st.columns([2,2])
# form = st.form(key="token_form")

# submit_button = form.form_submit_button(label="Submit")

# sender_token = form.text_input("Please enter the Token of the Sender User", placeholder="enter the sender token")    
# headers_sender = {
#     "Authorization": f"Token {sender_token}"
#     }
# username_sender_json = requests.get("https://kobo.drc.ngo/api/v2/access-logs/me/?format=json&limit=1", headers=headers_sender)b9b196762a596c94a74cf42ff9672bc6174c5d9f
# username_sender_data = json.loads(json.dumps(username_sender_json.json()))

# receiver_token = form.text_input("Please enter the Token of the Receiver User", placeholder="enter the receiver token")
# headers_receiver = {
#     "Authorization": f"Token {receiver_token}"
# }
# username_receiver_json = requests.get("https://kobo.drc.ngo/api/v2/access-logs/me/?format=json&limit=1", headers=headers_receiver)fed2149b17a4ce41b152ea21976b6239f46aee39
# username_receiver_data = json.loads(json.dumps(username_receiver_json.json()))

# with col1:
#     if(username_sender_json.status_code == 200):
#         st.header("SENDER")
#         st.markdown(f"**{username_sender_data['results'][0]['username']}**")

# with col2:
#     if(username_receiver_json.status_code == 200):
#         st.header("RECEIVER")
#         st.markdown(f"**{username_receiver_data['results'][0]['username']}**")

# assets_json = requests.get("https://kobo.drc.ngo/api/v2/assets/?format=json", headers=headers_sender)
# assets_data = json.loads(json.dumps(assets_json.json()))

# if assets_json.status_code == 200:
#     assets = assets_data['results']
#     df_assets = pd.DataFrame([
#         {"uid": asset['uid'], "name": asset["name"], "owner_username": asset["owner__username"]}
#         for asset in assets
#     ])

#     selected_names = st.multiselect(
#         "Select assets to transfer",
#         options= df_assets[df_assets["owner_username"] == username_sender_data['results'][0]['username']]["name"].tolist()
#     )

#     selected_uids = df_assets[df_assets["name"].isin(selected_names)]["uid"].tolist()

#     submit = st.button("submit")

#     if (submit and assets_json.status_code == 200):
#         recipient = f"https://kobo.drc.ngo/api/v2/users/{username_receiver_data['results'][0]['username']}/"
#         payload = {
#             "recipient": recipient,
#             "assets" : selected_uids
#         }

#         transfer_request = requests.post("https://kobo.drc.ngo/api/v2/project-ownership/invites/?format=json", headers=headers_sender, json=payload)

#         if transfer_request.status_code == 201:
#             st.success("Ownership transferred, pending acceptance. (you will receive an email to confirm the transfer. PLEASE IGNORE IT!!!)")
#         else:
#             st.error(transfer_request.status_code)
#             st.error(transfer_request.reason)

#         invites_url = json.loads(json.dumps(transfer_request.json()))
#         pathload = {
#             "status": "accepted"
#         }
#         patch_request = requests.patch(invites_url['url'], headers=headers_receiver, json=pathload)

#         if patch_request.status_code == 200:
#             st.success("Ownership transferred. (You will receive another email as well that the transfer was accepted. PLEASE IGNORE IT.)")
#         else:
#             st.error(patch_request.status_code)
#             st.error(patch_request.reason)