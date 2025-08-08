
import streamlit as st
import pandas as pd
import requests
import time

CONFIG = {
    "API_ROOT": "https://kobo.drc.ngo/api/v2"
}

st.set_page_config(page_title="Metadata Switchers", layout="wide")

st.title("🔁 Project Metadata Switchers")

st.markdown("""
Manage **bulk metadata updates** for your Kobo projects.  
Use the tabs below to switch between **PII** and **Function** switchers.
""")

# --- SESSION STATE INITIALIZATION ---
for key in ["owner_token", "owner_username", "df_assets_original_pii",
            "df_assets_edited_pii", "changes_pii", "assets_changes_pii",
            "df_assets_original_func", "df_assets_edited_func", "changes_func",
            "assets_changes_func", "header_owner", "confirm_apply_pii", "confirm_apply_func"]:
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
    tabs = st.tabs(["🔒 PII Switcher", "🏷️ Function Switcher"])

    # ----------- PII TAB -----------
    with tabs[0]:
        st.subheader("PII Switcher")
        # Fetch assets
        asset_resp = requests.get(f"{CONFIG['API_ROOT']}/assets/?format=json", headers=st.session_state.header_owner)
        if asset_resp.status_code == 200:
            assets_data = asset_resp.json()['results']
            df_assets = pd.DataFrame([
                {
                    "UID": a["uid"],
                    "Name": a["name"],
                    "owner_username": a["owner__username"],
                    "PII": a.get("settings", {}).get("collects_pii", {}).get("value", None)
                }
                for a in assets_data
            ])
            df_assets = df_assets[(df_assets["Name"] != "") & (df_assets["owner_username"] == st.session_state.owner_username)]
            st.session_state.df_assets_original_pii = df_assets[["UID", "Name", "PII"]].copy()

        column_config = {
            "PII": st.column_config.SelectboxColumn(
                "PII",
                help="Does this asset collect PII?",
                options=["Yes", "No"],
                required=True
            )
        }

        edited_df = st.data_editor(
            st.session_state.df_assets_original_pii,
            column_config=column_config,
            disabled=["UID", "Name"],
            use_container_width=True,
            num_rows="fixed",
            hide_index=True
        )
        st.session_state.df_assets_edited_pii = edited_df

        # Detect changes
        changes = edited_df[edited_df["PII"] != st.session_state.df_assets_original_pii["PII"]]
        st.session_state.changes_pii = changes
        st.session_state.assets_changes_pii = not changes.empty

        st.subheader("🔍 Review Changes")
        if changes.empty:
            st.success("✅ No changes detected.")
        else:
            st.dataframe(changes)
            if not st.session_state.get("confirm_apply_pii"):
                if st.button("✅ Confirm and Apply Changes", key="pii_confirm"):
                    st.session_state.confirm_apply_pii = True

        # Apply changes
        if st.session_state.assets_changes_pii and st.session_state.confirm_apply_pii:
            total = len(changes)
            success_count = 0
            progress_bar = st.progress(0, text="Initializing update...")

            for i, (_, row) in enumerate(changes.iterrows()):
                payload = {
                    "settings": {
                        "collects_pii": {
                            "label": row["PII"],
                            "value": row["PII"]
                        }
                    }
                }
                r = requests.patch(
                    f"{CONFIG['API_ROOT']}/assets/{row['UID']}/?format=json",
                    json=payload,
                    headers=st.session_state.header_owner
                )
                if r.status_code == 200:
                    success_count += 1
                else:
                    st.error(f"❌ Failed UID {row['UID']}: {r.status_code}")

                progress_bar.progress((i+1)/total, text=f"{success_count}/{total} updated...")
                time.sleep(0.05)

            st.success(f"🎉 Finished! {success_count} out of {total} assets updated.")
            st.session_state.confirm_apply_pii = False

    # ----------- FUNCTION TAB -----------
    with tabs[1]:
        st.subheader("Function Switcher")

        sector_options = [
            "Programme - Protection",
            "Programme - CCCM",
            "Programme - Economic Recovery",
            "Programme - HDP",
            "Programme - Shelter & Settlement",
            "Programme - WASH",
            "MEAL",
            "Information Management",
            "Safety",
            "Grants Management",
            "HR",
            "Supply Chain",
            "IT",
            "Finance",
            "Risk and Compliance",
            "Advocacy and Communication",
            "Safeguarding and CoC",
            "Programme Development and Quality",
            "Other"
        ]

        # Fetch assets
        asset_resp = requests.get(f"{CONFIG['API_ROOT']}/assets/?format=json", headers=st.session_state.header_owner)
        if asset_resp.status_code == 200:
            assets_data = asset_resp.json()['results']
            df_assets = pd.DataFrame([
                {
                    "UID": a["uid"],
                    "Name": a["name"],
                    "owner_username": a["owner__username"],
                    "Function": a.get("settings", {}).get("sector", {}).get("value", None)
                }
                for a in assets_data
            ])
            df_assets = df_assets[(df_assets["Name"] != "") & (df_assets["owner_username"] == st.session_state.owner_username)]
            st.session_state.df_assets_original_func = df_assets[["UID", "Name", "Function"]].copy()

        column_config = {
            "Function": st.column_config.SelectboxColumn(
                "Function",
                help="Select the function/sector for this asset",
                options=sector_options,
                required=True
            )
        }

        edited_df = st.data_editor(
            st.session_state.df_assets_original_func,
            column_config=column_config,
            disabled=["UID", "Name"],
            use_container_width=True,
            num_rows="fixed",
            hide_index=True
        )
        st.session_state.df_assets_edited_func = edited_df

        # Detect changes
        changes = edited_df[edited_df["Function"] != st.session_state.df_assets_original_func["Function"]]
        st.session_state.changes_func = changes
        st.session_state.assets_changes_func = not changes.empty

        st.subheader("🔍 Review Changes")
        if changes.empty:
            st.success("✅ No changes detected.")
        else:
            st.dataframe(changes)
            if not st.session_state.get("confirm_apply_func"):
                if st.button("✅ Confirm and Apply Changes", key="func_confirm"):
                    st.session_state.confirm_apply_func = True

        # Apply changes
        if st.session_state.assets_changes_func and st.session_state.confirm_apply_func:
            total = len(changes)
            success_count = 0
            progress_bar = st.progress(0, text="Initializing update...")

            for i, (_, row) in enumerate(changes.iterrows()):
                payload = {
                    "settings": {
                        "sector": {
                            "label": row["Function"],
                            "value": row["Function"]
                        }
                    }
                }
                r = requests.patch(
                    f"{CONFIG['API_ROOT']}/assets/{row['UID']}/?format=json",
                    json=payload,
                    headers=st.session_state.header_owner
                )
                if r.status_code == 200:
                    success_count += 1
                else:
                    st.error(f"❌ Failed UID {row['UID']}: {r.status_code}")

                progress_bar.progress((i+1)/total, text=f"{success_count}/{total} updated...")
                time.sleep(0.05)

            st.success(f"🎉 Finished! {success_count} out of {total} assets updated.")
            st.session_state.confirm_apply_func = False
