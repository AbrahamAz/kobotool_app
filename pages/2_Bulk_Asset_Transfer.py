import streamlit as st
import requests
import json
import pandas as pd

st.title("Transfer Assets in Bulk")

st.markdown("This app is used to transfer assets in bulk.")

col1, col2 = st.columns([2,2])
form = st.form(key="token_form")

submit_button = form.form_submit_button(label="Submit")

sender_token = form.text_input("Please enter the Token of the Sender User", placeholder="enter the sender token")    
headers_sender = {
    "Authorization": f"Token {sender_token}"
    }
username_sender_json = requests.get("https://kobo.drc.ngo/api/v2/access-logs/me/?format=json&limit=1", headers=headers_sender)
username_sender_data = json.loads(json.dumps(username_sender_json.json()))

receiver_token = form.text_input("Please enter the Token of the Receiver User", placeholder="enter the receiver token")
headers_receiver = {
    "Authorization": f"Token {receiver_token}"
}
username_receiver_json = requests.get("https://kobo.drc.ngo/api/v2/access-logs/me/?format=json&limit=1", headers=headers_receiver)
username_receiver_data = json.loads(json.dumps(username_receiver_json.json()))

with col1:
    if(username_sender_json.status_code == 200):
        st.header("SENDER")
        st.markdown(f"**{username_sender_data['results'][0]['username']}**")

with col2:
    if(username_receiver_json.status_code == 200):
        st.header("RECEIVER")
        st.markdown(f"**{username_receiver_data['results'][0]['username']}**")

assets_json = requests.get("https://kobo.drc.ngo/api/v2/assets/?format=json", headers=headers_sender)
assets_data = json.loads(json.dumps(assets_json.json()))

if assets_json.status_code == 200:
    assets = assets_data['results']
    df_assets = pd.DataFrame([
        {"uid": asset['uid'], "name": asset["name"], "owner_username": asset["owner__username"]}
        for asset in assets
    ])

    selected_names = st.multiselect(
        "Select assets to transfer",
        options= df_assets[df_assets["owner_username"] == username_sender_data['results'][0]['username']]["name"].tolist()
    )

    selected_uids = df_assets[df_assets["name"].isin(selected_names)]["uid"].tolist()

    submit = st.button("submit")

    if (submit and assets_json.status_code == 200):
        recipient = f"https://kobo.drc.ngo/api/v2/users/{username_receiver_data['results'][0]['username']}/"
        payload = {
            "recipient": recipient,
            "assets" : selected_uids
        }

        transfer_request = requests.post("https://kobo.drc.ngo/api/v2/project-ownership/invites/?format=json", headers=headers_sender, json=payload)

        if transfer_request.status_code == 201:
            st.success("Ownership transferred, pending acceptance. (you will receive an email to confirm the transfer. PLEASE IGNORE IT!!!)")
        else:
            st.error(transfer_request.status_code)
            st.error(transfer_request.reason)

        invites_url = json.loads(json.dumps(transfer_request.json()))
        pathload = {
            "status": "accepted"
        }
        patch_request = requests.patch(invites_url['url'], headers=headers_receiver, json=pathload)

        if patch_request.status_code == 200:
            st.success("Ownership transferred. (You will receive another email as well that the transfer was accepted. PLEASE IGNORE IT.)")
        else:
            st.error(patch_request.status_code)
            st.error(patch_request.reason)