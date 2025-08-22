import streamlit as st
import requests
import pandas as pd
import json

CONFIG = {
    "API_ROOT": "https://kobo.drc.ngo/api/v2"
}

st.set_page_config(page_title="Project Overview Dashboard",
                   layout = "wide")

st.title("📊 Project Overview Dashboard")

st.markdown("""
This dashboard provides an overview of all projects owned by a Kobo user.
Enter your **Kobo API Token** to get started.
""")

for key in ["owner_token", "owner_username","headers_owner"]:
    if key not in st.session_state:
        st.session_state[key] = None


# --- AUTH FORM ---
if "owner_username" not in st.session_state or st.session_state.owner_username is None:
    auth_box = st.empty()  # placeholder so we can clear the form immediately
    with auth_box.form(key="token_form", clear_on_submit=True):
        st.subheader("🔐 API Token")
        owner_token = st.text_input("Owner User Token", placeholder="Paste your API token", type="password")
        submit_tokens = st.form_submit_button("Authenticate")

        if submit_tokens:
            headers_owner = {"Authorization": f"Token {owner_token}"}
            resp = requests.get(f"{CONFIG['API_ROOT']}/access-logs/me/?format=json&limit=1", headers=headers_owner)

            if resp.status_code == 200:
                st.session_state.owner_token = owner_token
                st.session_state.owner_username = resp.json()['results'][0]['username']
                st.session_state.header_owner = headers_owner  # keep this exact key name consistent everywhere
                # instantly remove the form and rerun so the tabs show up right away
                auth_box.empty()
                st.rerun()
            else:
                st.error("❌ Invalid token. Please try again.")

# --- MAIN TABS ---
if st.session_state.owner_username:
    st.subheader("✅ Authenticated Users")
    st.markdown("**👤 Owner Username**")
    st.info(st.session_state.owner_username)

    asset_resp = requests.get(f"{CONFIG['API_ROOT']}/assets/?format=json", headers=st.session_state.header_owner)
    if asset_resp.status_code == 200:
        assets = asset_resp.json()['results']
        owned_assets = [a for a in assets if (a["owner__username"] == st.session_state.owner_username) & (a['name'] != "")]

        if not owned_assets:
            st.warning("No owned assets found.")
        else:
            st.markdown(f"### 🗂️ You own {len(owned_assets)} projects.")
            asset_names = [f"{a['name']} ({a['uid']})" for a in owned_assets]
            asset_lookup = {f"{a['name']} ({a['uid']})": a for a in owned_assets}

            selected_asset_display = st.selectbox("Select a project to inspect",
                                                  options = asset_names)
            
            selected_asset = asset_lookup[selected_asset_display]

            uid = selected_asset['uid']
            deployed = selected_asset.get('deployment__active', False)
            deployed_date = selected_asset.get('date_deployed', None)
            last_submissions = selected_asset.get('deployment__last_submission_time', None)
            form_name = selected_asset['name']
            form_url = selected_asset['url']
            asset_created = selected_asset['date_created']
