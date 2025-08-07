import streamlit as st
import pandas as pd
import requests
import json
import time

CONFIG = {
    "API_ROOT": "https://kobo.drc.ngo/api/v2"
}

st.set_page_config(page_title="PII Information Switcher", layout="wide")

st.title("🔁 Switch PII Metadata")

st.markdown("""
            This tool allows you to **bulk update the PII metadata** for your Kobo projects.  
            Enter the API token of the **project owner** to proceed.
            """)

with st.expander("ℹ️ How it works"):
    st.markdown("""
                1. Enter the **API Token** of the project owner.
                2. Authenticate and fetch the project list.
                3. Modify the **PII field** in the editable table.
                4. Submit your changes and watch them update in real-time.
                """)
    
for key in ["owner_token", "owner_username", "df_assets_original",
             "df_assets_edited","changes","assets_changes",
             "headers_owner","confirm_apply"]:
    if key not in st.session_state:
        st.session_state[key] = None


# ----- FORM TOKEN ------
if not st.session_state.owner_username:
    with st.form(key = "token_form"):
        st.subheader("🔐 API Token")

        owner_token = st.text_input("Owner User Token", placeholder="Paste your API token", type="password")

        submit_tokens = st.form_submit_button("Authenticate")

        if submit_tokens:
            headers_owner = {"Authorization": f"Token {owner_token}"}
            st.session_state.header_owner = headers_owner
            owner_resp = requests.get(f"{CONFIG['API_ROOT']}/access-logs/me/?format=json&limit=1", headers=st.session_state.header_owner)

            if owner_resp.status_code == 200:
                st.session_state.owner_token = owner_token
                st.session_state.owner_username = owner_resp.json()['results'][0]['username']
                st.success("✅ Token verified! You are now authenticated.")
                
            else:
                st.error("❌ Invalid token. Please try again.")

# ------ MAIN INTERFACE -------
if st.session_state.owner_username:
    st.subheader("👤 Authenticated Owner:")
    st.info(f"**Username:** {st.session_state.owner_username}")

    asset_resp = requests.get(f"{CONFIG['API_ROOT']}/assets/?format=json", headers=st.session_state.header_owner)
    if asset_resp.status_code == 200:
        assets_data = asset_resp.json()['results']
        df_assets_original = pd.DataFrame([
            {"UID": asset["uid"], "Name": asset["name"], "owner_username": asset["owner__username"], "PII": asset.get("settings", {}).get("collects_pii", {}).get("value", None)}
            for asset in assets_data
        ])
        df_assets_original = df_assets_original[(df_assets_original["Name"] != "") & (df_assets_original["owner_username"] == st.session_state.owner_username)]
        st.session_state.df_assets_original = df_assets_original[["UID", "Name", "PII"]].copy()


if st.session_state.owner_username:
    st.divider()
    st.subheader("✏️ Edit PII Values")
    # Set column configs for data_editor
    column_config = {
        "PII": st.column_config.SelectboxColumn(
            "PII",
            help="Does this asset collect PII?",
            options=["Yes", "No"],
            required=True
        )
    }

    # Editable DataFrame
    edited_df = st.data_editor(
        st.session_state.df_assets_original,
        column_config=column_config,
        disabled=["UID", "Name"],  # Disable editing for these columns
        use_container_width=True,
        num_rows="fixed",        # Prevent adding/removing rows
        hide_index=True    
    )
    st.session_state.df_assets_edited = edited_df
    
    # if st.button("📤 Submit Changes"):
    #     st.session_state.assets_edited = True
    #     st.session_state.confirm_apply = False

if st.session_state.df_assets_edited is not None and st.session_state.df_assets_original is not None:
    original_df = st.session_state.df_assets_original
    edited_df = st.session_state.df_assets_edited
    changes = edited_df[edited_df["PII"] != original_df["PII"]]
    st.session_state.changes = changes
    st.session_state.assets_changes = not changes.empty

    st.divider()
    st.subheader("🔍 Review Changes")

    if changes.empty:
        st.success("✅ No changes detected.")
        st.session_state.assets_changes = False
        st.session_state.confirm_apply = False
    else:
        st.dataframe(changes)
        st.session_state.changes = changes
        st.session_state.assets_changes = True
        # Debug (optional)
        with st.expander("🧾 Compare Original vs Edited"):
            st.write("Original Data")
            st.dataframe(st.session_state.df_assets_original)
            st.write("Edited Data")
            st.dataframe(edited_df)

        if not st.session_state.get("confirm_apply"):
            if st.button("✅ Confirm and Apply Changes"):
                st.session_state.confirm_apply = True
                # st.rerun()

if st.session_state.assets_changes and st.session_state.confirm_apply:
    st.divider()
    st.subheader("🚀 Apply Changes to Kobo")

    changes = st.session_state.changes
    total = len(changes)
    success_count = 0

    progress_bar = st.progress(0, text="Initializing update...")
    status_placeholder = st.empty()

    for i, (_, row) in enumerate(changes.iterrows()):
        uid = row["UID"]
        pii_value = row["PII"]
        url = f"{CONFIG['API_ROOT']}/assets/{uid}/?format=json"
        payload = {
            "settings": {
                "collects_pii": {
                    "label": pii_value,
                    "value": pii_value
                }
            }
        }

        response = requests.patch(
            url,
            json=payload,
            headers=st.session_state.header_owner
        )

        if response.status_code == 200:
            success_count += 1
        else:
            st.error(f"❌ Failed to update UID {uid}: {response.status_code} - {response.text}")

        progress_bar.progress(success_count / total, text=f"✅ {success_count}/{total} updated...")
        time.sleep(0.05)

    progress_bar.empty()
    st.success(f"🎉 Finished! {success_count} out of {total} assets updated successfully.")
    st.session_state.confirm_apply = False
    st.session_state.assets_changes = False