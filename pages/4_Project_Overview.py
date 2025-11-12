import streamlit as st
import requests
import pandas as pd
import json
import re
from pandas import json_normalize



st.set_page_config(page_title="Project Overview Dashboard",
                   layout = "wide")

st.title("📊 Project Overview Dashboard")

st.markdown("""
This dashboard provides an overview of all projects owned by a Kobo user.
Enter your **Kobo API Token** to get started.
""")

if "kobo_url" not in st.session_state:
    st.session_state.kobo_url = None

kobo_url = st.sidebar.text_input("Please enter the kobo url", value = "https://kobo.drc.ngo")
st.session_state.kobo_url = kobo_url

CONFIG = {
    "API_ROOT": f"{st.session_state.kobo_url}/api/v2"
}

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

    assets_resp = requests.get(f"{CONFIG['API_ROOT']}/assets/?format=json", headers=st.session_state.header_owner)
    if assets_resp.status_code == 200:
        assets = assets_resp.json()['results']
        owned_assets = [a for a in assets if (a["owner__username"] == st.session_state.owner_username) & (a['name'] != "") & (a['deployment_status'] == "deployed")]

        if not owned_assets:
            st.warning("No owned assets found.")
        else:
            st.markdown(f"### 🗂️ You own {len(owned_assets)} projects.")
            assets_names = [f"{a['name']} ({a['uid']})" for a in owned_assets]
            assets_lookup = {f"{a['name']} ({a['uid']})": a for a in owned_assets}

            selected_asset_display = st.selectbox("Select a project to inspect",
                                                  options = assets_names)
            
            selected_asset = assets_lookup[selected_asset_display]

            asset_uid = selected_asset['uid']

            asset_resp = requests.get(f"{CONFIG['API_ROOT']}/assets/{asset_uid}/?format=json", headers=st.session_state.header_owner)
            if asset_resp.status_code == 200:
                asset = asset_resp.json()
                if asset["settings"]["sector"]["label"] == None:
                    sector = "The Sector Metadata is missing. Please fill it."
                else:
                    sector = asset["settings"]["sector"]["label"]
                if asset.get("settings", []).get("collects_pii", None) == None:
                     pii = "The PII Metadata is missing. Please fill it."

                else:
                    pii = asset["settings"]["collects_pii"]["label"]

                date_created = asset["date_created"]
                date_deployed = asset["date_deployed"]
                date_modified = asset["date_modified"]
                countries = asset.get("settings",[]).get("country",[])
                if countries != []:
                    df_country = pd.DataFrame([
                        {
                            "Country Label": c["label"],
                            "Country Code": c["value"]
                        } for c in countries
                    ])
                else:
                    df_country = "The Country Metadata is missing. Please fill it."
                
                # ---- INFOGRTAPHIC CUBES
                col1, col2, col3 = st.columns(3)
                col4, col5, col6 = st.columns(3)
                with st.expander("ℹ️ Metadata"):
                    # with col1:
                    st.metric("📅 Date Created", date_created[:10])
                    st.metric("📅 Date Deployed", date_deployed[:10])
                    st.metric("📅 Date Created", date_modified[:10])
                    if asset.get("settings", []).get("collects_pii", None) == None:
                        st.metric("🔐 Collection of PII", pii)
                    else:
                        st.metric("🔐 Collection of PII", pii)
                    if asset["settings"]["sector"]["label"] == None:
                        st.metric("📛 Sector Name", sector)
                    else:
                        st.metric("📛 Sector Name", sector)
                    if countries != []:
                        st.metric(" Country Name", "; ".join(df_country['Country Label']))
                    else:
                        st.metric(" Country Name", df_country)
                
                versions = asset.get("deployed_versions", None).get("results", [])

                if versions:
                    df_versions = pd.DataFrame([
                        {
                            "Version ID": v["uid"],
                            "Date Deployed": v["date_deployed"][:10],
                            "Date Modified": v["date_modified"][:10]
                        } for v in versions
                    ])
                    with st.expander("📦 Versions"):
                        st.dataframe(df_versions)

                xls_data_download = asset.get("deployment__data_download_links", None).get("xls", None)
                csv_data_download = asset.get("deployment__data_download_links", None).get("csv", None)
                if (xls_data_download) and (csv_data_download):
                    with st.expander("🗄️ Data Download"):
                            st.link_button("XLSX", xls_data_download)
                            st.link_button("CSV", csv_data_download)
                form_link = asset.get("deployment__links", None).get("iframe_url", None)
                download_form_link = f"{CONFIG['API_ROOT']}/assets/{asset_uid}/?format=xls"
                if (form_link):
                    with st.expander("🔗 Form Web Link"):
                        st.link_button("XLS Form Download",download_form_link)
                        st.components.v1.iframe(form_link, height = 600)

                submission_count = asset["deployment__submission_count"]
                date_last_submission = asset["deployment__last_submission_time"][:10]
                
                if (submission_count):
                    with st.expander("⬆️ Submissions"):
                        st.metric("Number of Submissions", submission_count)
                        st.metric("Date of Last Submission", date_last_submission)

                permissions = asset["permissions"]
                if permissions:
                    df_permissions = pd.DataFrame([
                        {
                            "Username": str(re.findall(r"users/([^/?]+)",p["user"])[0]),
                            "Permission": str(re.findall(r"permissions/([^/?]+)", p["permission"])[0]),
                            "Label": p["label"],

                        } for p in permissions
                    ])
                    with st.expander("🔑 Permissions"):
                        st.dataframe(df_permissions[df_permissions["Username"] != "AnonymousUser"])
                
                data_resp = requests.get(f"{CONFIG['API_ROOT']}/assets/{asset_uid}/data/?format=json", headers=st.session_state.header_owner)
                if data_resp.status_code == 200:
                    data = data_resp.json()["results"]
                    data_df = json_normalize(data)

                    with st.expander("📊 Data"):
                        st.dataframe(data_df)
