
import streamlit as st
import pandas as pd
import requests
import time
import json
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode


st.set_page_config(page_title="Metadata Switchers", layout="wide")

st.title("🔁 Project Metadata Switchers")

st.markdown("""
Manage **bulk metadata updates** for your Kobo projects.
Use the tabs below to switch between **PII**, **Function**, **Legal Entity** and **Donor** switchers.
""")

DONOR_OPTIONS = [
    {"name": "echo", "label": "ECHO"},
    {"name": "danida", "label": "DANIDA"},
    {"name": "ec_development", "label": "EC Development"},
    {"name": "fcdo", "label": "FCDO"},
    {"name": "unhcr", "label": "UNHCR"},
    {"name": "ocha_cbpfs", "label": "OCHA CBPFs"},
    {"name": "prm", "label": "PRM"},
    {"name": "wra", "label": "WRA"},
    {"name": "afd", "label": "AFD"},
    {"name": "cdcs", "label": "CDCS"},
    {"name": "sdc", "label": "SDC"},
    {"name": "sida", "label": "Sida"},
    {"name": "bmz", "label": "BMZ"},
    {"name": "gffo", "label": "GFFO"},
    {"name": "giz", "label": "GIZ"},
    {"name": "kfw", "label": "KfW"},
    {"name": "dmfa", "label": "Danish Ministry of Foreign Affairs"},
    {"name": "bha", "label": "BHA"},
    {"name": "dutch_mfa", "label": "Dutch Ministry of Foreign Affairs"},
    {"name": "pool_funds", "label": "Pool Funds"},
    {"name": "augustinus_fonden", "label": "Augustinus Fonden"},
    {"name": "euic", "label": "EUIC"},
    {"name": "finm", "label": "FINM"},
    {"name": "frem", "label": "FREM"},
    {"name": "hgbf", "label": "HGBF"},
    {"name": "hoffmans_and_husmans", "label": "Hoffmans And Husmans"},
    {"name": "mofa", "label": "MOFA"},
    {"name": "norad", "label": "NORAD"},
    {"name": "novo_nordisk", "label": "Novo Nordisk"},
    {"name": "okf", "label": "OKF"},
    {"name": "pfru", "label": "PFRU"},
    {"name": "pmra", "label": "PMRA"},
    {"name": "pspu", "label": "PSPU"},
    {"name": "sdcs", "label": "SDCS"},
    {"name": "unhc", "label": "UNHC"},
    {"name": "villum_fundation", "label": "Villum Fundation"},
    {"name": "other", "label": "Other"},
]
DONOR_LABEL_BY_NAME = {d["name"]: d["label"] for d in DONOR_OPTIONS}
if "kobo_url" not in st.session_state:
    st.session_state.kobo_url = None

kobo_url = st.sidebar.text_input("Please enter the kobo url", value = "https://kobo.drc.ngo")
st.session_state.kobo_url = kobo_url

CONFIG = {
    "API_ROOT": f"{st.session_state.kobo_url}/api/v2"
}


# --- SESSION STATE INITIALIZATION ---
for key in ["owner_token", "owner_username", "df_assets_original_pii",
            "df_assets_edited_pii", "changes_pii", "assets_changes_pii",
            "df_assets_original_func", "df_assets_edited_func", "changes_func",
            "df_assets_original_legalentity", "df_assets_edited_legalentity",
            "changes_legalentity", "assets_changes_legalentity", "confirm_apply_legalentity",
            "assets_changes_func", "header_owner", "confirm_apply_pii", "confirm_apply_func",
            "df_assets_original_donor", "df_assets_edited_donor", "changes_donor",
            "assets_changes_donor", "confirm_apply_donor", "donor_extra_metadata_by_uid"]:
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
            try:
                # "/me/" is Kobo's lightweight "who am I" endpoint — a single-row
                # profile lookup. Deliberately NOT using "/api/v2/access-logs/me/"
                # here: that endpoint scans the account's full access-log history,
                # which is slow for busy accounts and was observed returning a
                # straight-up 502 Bad Gateway (the backend erroring out, not just
                # being slow) rather than a clean response.
                resp = requests.get(
                    f"{st.session_state.kobo_url}/me/?format=json",
                    headers=headers_owner,
                    timeout=30
                )
            except requests.exceptions.Timeout:
                st.error("⏱️ The token check timed out after 30s. Try again — this may be a transient server-side issue.")
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Could not reach the Kobo server: {e}")
            else:
                if resp.status_code == 200:
                    username = resp.json().get("username")
                    if username:
                        st.session_state.owner_token = owner_token
                        st.session_state.owner_username = username
                        st.session_state.header_owner = headers_owner  # keep this exact key name consistent everywhere
                        # instantly remove the form and rerun so the tabs show up right away
                        auth_box.empty()
                        st.rerun()
                    else:
                        st.error(f"⚠️ Token is valid, but the response had no username: {resp.text[:500]}")
                elif resp.status_code == 401:
                    st.error("❌ Invalid token. Please try again.")
                else:
                    st.error(f"❌ Authentication failed (HTTP {resp.status_code}): {resp.text[:500]}")

# --- MAIN TABS ---
if st.session_state.owner_username:
    st.subheader("✅ Authenticated Users")
    st.markdown("**👤 Owner Username**")
    st.info(st.session_state.owner_username)

    tabs = st.tabs(["🔒 PII Switcher", "🏷️ Function Switcher", "🌍 Legal Entity Switcher", "💰 Donor Switcher"])

    # ----------- PII TAB -----------
    with tabs[0]:
        st.subheader("PII Switcher")
        # Fetch assets
        asset_resp = requests.get(f"{CONFIG['API_ROOT']}/assets/?format=json&limit=100000", headers=st.session_state.header_owner)
        if asset_resp.status_code == 200:
            assets_data = asset_resp.json()['results']
            df_assets = pd.DataFrame([
                {
                    "UID": a["uid"],
                    "Name": a["name"],
                    "owner_username": a["owner__username"],
                    "PII": (
                        a.get("settings", {}).get("collects_pii", {}).get("value")
                        if a.get("settings", {}).get("collects_pii") is not None
                        else a.get("settings", {}).get("collect_pii")
                    )
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
        asset_resp = requests.get(f"{CONFIG['API_ROOT']}/assets/?format=json&limit=100000", headers=st.session_state.header_owner)
        if asset_resp.status_code == 200:
            assets_data = asset_resp.json()['results']
            df_assets = pd.DataFrame([
                {
                    "UID": a["uid"],
                    "Name": a["name"],
                    "owner_username": a["owner__username"],
                    "Function": (
                        a.get("settings", {}).get("sector", {}).get("value", None)
                        if a.get("settings", {}).get("sector")
                        else None
                        )
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
     # ----------- LEGAL ENTITY TAB -----------
    with tabs[2]:
        st.subheader("Legal Entity Switcher - Specific for kobo.drc.ngo")

        legalentity_options = [
            "DKHQ - DKHQ",
            "INET Implementing Network - INET",
            "Myanmar - MMR",
            "Serbia - SRB",
            "Bosnia and Herzegovina - BIH",
            "Ukraine - UKR",
            "Poland - POL",
            "Kosovo - XKX",
            "Bangladesh - BGD",
            "Afghanistan - AFG",
            "Georgia - GEO",
            "Italy - ITA",
            "Greece - GRC",
            "Mali - MLI",
            "Niger - NER",
            "Nigeria - NGA",
            "Venezuela - VEN",
            "Mexico - MEX",
            "Cameroon - CMR",
            "Chad - TCD",
            "Burkina Faso - BFA",
            "Central African Republic - CAF",
            "Colombia - COL",
            "Syria - SYR",
            "Tunisia - TUN",
            "Yemen - YEM",
            "Algeria - DZA",
            "Iraq - IRQ",
            "Jordan - JOR",
            "Lebanon - LBN",
            "Libya - LBY",
            "Somalia - SOM",
            "South Sudan - SSD",
            "Sudan - SDN",
            "Tanzania - TZA",
            "Uganda - UGA",
            "Burundi - BDI",
            "Djibouti - DJI",
            "Ethiopia - ETH",
            "Kenya - KEN",
            "East Africa & Great Lakes - RO01",
            "Middle East & North Africa - RO02",
            "West Africa & Americas - RO03",
            "Asia & Europe - RO05",
            "Türkiye - TUR",
            "Occupied Palestine Territory - OPT",
            "Democratic Republic of the Congo - COD"
        ]

        # Fetch assets
        asset_resp = requests.get(f"{CONFIG['API_ROOT']}/assets/?format=json&limit=100000", headers=st.session_state.header_owner)
        if asset_resp.status_code == 200:
            assets_data = asset_resp.json()['results']
            df_assets = pd.DataFrame([
                {
                    "UID": a["uid"],
                    "Name": a["name"],
                    "owner_username": a["owner__username"],
                    "deployment_status": a["deployment_status"],
                    "Legal Entity": (
                            a.get("settings", {}).get("operational_purpose", {}).get("value")
                            if a.get("settings", {}).get("operational_purpose") 
                            else None
                            )
                }
                for a in assets_data
            ])
            df_assets = df_assets[(df_assets["Name"] != "") & (df_assets["owner_username"] == st.session_state.owner_username) & (df_assets["deployment_status"].isin(["deployed","archived"]))]
            st.session_state.df_assets_original_legalentity = df_assets[["UID", "Name", "Legal Entity"]].copy()

        column_config = {
            "Legal Entity": st.column_config.SelectboxColumn(
                "Legal Entity",
                help="Select the legal entity for this asset",
                options=legalentity_options,
                required=True
            )
        }

        edited_df = st.data_editor(
            st.session_state.df_assets_original_legalentity,
            column_config=column_config,
            disabled=["UID", "Name"],
            use_container_width=True,
            num_rows="fixed",
            hide_index=True
        )
        st.session_state.df_assets_edited_legalentity = edited_df

        # Detect changes
        changes = edited_df[edited_df["Legal Entity"] != st.session_state.df_assets_original_legalentity["Legal Entity"]]
        st.session_state.changes_legalentity = changes
        st.session_state.assets_changes_legalentity = not changes.empty

        st.subheader("🔍 Review Changes")
        if changes.empty:
            st.success("✅ No changes detected.")
        else:
            st.dataframe(changes)
            if not st.session_state.get("confirm_apply_legalentity"):
                if st.button("✅ Confirm and Apply Changes", key="legalentity_confirm"):
                    st.session_state.confirm_apply_legalentity = True

        # Apply changes
        if st.session_state.assets_changes_legalentity and st.session_state.confirm_apply_legalentity:
            total = len(changes)
            success_count = 0
            progress_bar = st.progress(0, text="Initializing update...")

            for i, (_, row) in enumerate(changes.iterrows()):
                payload = {
                    "settings": {
                        "operational_purpose": {
                            "label": row["Legal Entity"],
                            "value": row["Legal Entity"]
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
            st.session_state.confirm_apply_legalentity = False

    # ----------- DONOR TAB -----------
    with tabs[3]:
        st.subheader("Donor Switcher")

        donor_labels = [d["label"] for d in DONOR_OPTIONS]
        donor_name_by_label = {d["label"]: d["name"] for d in DONOR_OPTIONS}

        # Fetch assets
        asset_resp = requests.get(f"{CONFIG['API_ROOT']}/assets/?format=json&limit=100000", headers=st.session_state.header_owner)
        if asset_resp.status_code == 200:
            assets_data = asset_resp.json()['results']

            extra_metadata_by_uid = {}
            rows = []
            for a in assets_data:
                extra_metadata = a.get("settings", {}).get("extra_metadata") or {}
                extra_metadata_by_uid[a["uid"]] = extra_metadata
                donor_names = set(extra_metadata.get("project_donors") or [])
                # keep a fixed, canonical label order so it matches what the in-cell
                # editor produces (avoids false "changed" rows from reordering only)
                donor_str = ", ".join(d["label"] for d in DONOR_OPTIONS if d["name"] in donor_names)
                rows.append({
                    "UID": a["uid"],
                    "Name": a["name"],
                    "owner_username": a["owner__username"],
                    "Donors": donor_str
                })

            st.session_state.donor_extra_metadata_by_uid = extra_metadata_by_uid
            df_assets = pd.DataFrame(rows)
            df_assets = df_assets[(df_assets["Name"] != "") & (df_assets["owner_username"] == st.session_state.owner_username)]
            st.session_state.df_assets_original_donor = df_assets[["UID", "Name", "Donors"]].copy()

        # Custom AG Grid (Community edition, no license needed) checklist popup editor,
        # since st.data_editor has no native multi-select column and AG Grid's own
        # multi-select "Rich Select" editor is an Enterprise-only feature.
        multiselect_editor = JsCode(f"""
        class DonorMultiSelectEditor {{
            init(params) {{
                this.options = {donor_labels!r};
                var current = (params.value || '').split(',').map(s => s.trim()).filter(s => s.length > 0);
                this.selected = new Set(current);
                this.eGui = document.createElement('div');
                this.eGui.style.background = 'var(--ag-background-color, white)';
                this.eGui.style.border = '1px solid #ccc';
                this.eGui.style.borderRadius = '4px';
                this.eGui.style.padding = '6px';
                this.eGui.style.maxHeight = '280px';
                this.eGui.style.overflowY = 'auto';
                this.eGui.style.boxShadow = '0 2px 8px rgba(0,0,0,0.2)';
                this.eGui.style.minWidth = '240px';
                var self = this;
                this.options.forEach(function(opt) {{
                    var label = document.createElement('label');
                    label.style.display = 'block';
                    label.style.padding = '3px 4px';
                    label.style.cursor = 'pointer';
                    label.style.fontSize = '13px';
                    var checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.style.marginRight = '6px';
                    checkbox.checked = self.selected.has(opt);
                    checkbox.addEventListener('change', function(e) {{
                        if (e.target.checked) {{ self.selected.add(opt); }} else {{ self.selected.delete(opt); }}
                    }});
                    label.appendChild(checkbox);
                    label.appendChild(document.createTextNode(opt));
                    self.eGui.appendChild(label);
                }});
            }}
            getGui() {{ return this.eGui; }}
            afterGuiAttached() {{ }}
            getValue() {{ return this.options.filter((o) => this.selected.has(o)).join(', '); }}
            isPopup() {{ return true; }}
            isCancelBeforeStart() {{ return false; }}
            isCancelAfterEnd() {{ return false; }}
        }}
        """)

        gb = GridOptionsBuilder.from_dataframe(st.session_state.df_assets_original_donor)
        gb.configure_default_column(editable=False, resizable=True)
        gb.configure_column("UID", editable=False)
        gb.configure_column("Name", editable=False, flex=1)
        gb.configure_column(
            "Donors",
            editable=True,
            cellEditor=multiselect_editor,
            cellEditorPopup=True,
            flex=2,
            tooltipField="Donors"
        )
        grid_options = gb.build()
        # from_dataframe() defaults to an imperative "fitGridWidth" auto-size pass
        # (it also silently disables our colDef.flex settings). That pass runs at
        # mount time, when a st.tabs() panel can still report 0px width, leaving
        # columns stuck at zero width. Disable it and rely on CSS flex instead,
        # which AG Grid recalculates live via ResizeObserver — no race.
        grid_options["autoSizeStrategy"] = None
        # With only 3 columns, column virtualization buys nothing but risk: if the
        # grid's very first width measurement (inside a st.tabs() panel) comes back
        # too small/zero, virtualization can leave a column permanently un-rendered
        # until a manual resize. Force every column to always render.
        grid_options["suppressColumnVirtualisation"] = True

        grid_resp = AgGrid(
            st.session_state.df_assets_original_donor,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.VALUE_CHANGED,
            data_return_mode=DataReturnMode.AS_INPUT,
            allow_unsafe_jscode=True,
            theme="streamlit",
            # st.tabs() renders inactive panels with 0 width; AG Grid measures its
            # container at mount time and can get stuck at width:0 when it first
            # mounts inside a tab. Force the container to the panel's real width so
            # AG Grid's own ResizeObserver recalculates a correct layout.
            custom_css={
                "#gridContainer": {"width": "100% !important"},
                ".ag-root-wrapper": {"width": "100% !important"},
            },
            # Force JSON transport instead of Arrow: with enough rows, st_aggrid's
            # 'auto' mode switches to Arrow, and this server's PyArrow encodes
            # string columns as LargeUtf8 — a type the component's bundled
            # Arrow-JS decoder doesn't recognize, crashing before anything mounts
            # ("Uncaught Error: Unrecognized type: 'LargeUtf8' (20)"). JSON avoids
            # that binary decode path entirely.
            use_json_serialization=True,
            key="donor_aggrid"
        )
        original_df = st.session_state.df_assets_original_donor
        # grid_resp["data"] isn't consistently a DataFrame across environments:
        # it's None before the component has sent anything back (e.g. first
        # render, no edits yet), and with use_json_serialization=True some
        # versions return a raw JSON records string instead of a parsed
        # DataFrame. Normalize all of that to a DataFrame here.
        raw_data = grid_resp["data"]
        if raw_data is None:
            edited_df = original_df
        elif isinstance(raw_data, pd.DataFrame):
            edited_df = raw_data
        elif isinstance(raw_data, str):
            edited_df = pd.DataFrame(json.loads(raw_data))
        else:
            edited_df = pd.DataFrame(raw_data)
        st.session_state.df_assets_edited_donor = edited_df

        # Detect changes
        merged = edited_df.merge(original_df, on="UID", suffixes=("_new", "_orig"))
        changed_mask = merged["Donors_new"] != merged["Donors_orig"]
        changes = merged[changed_mask][["UID", "Name_new", "Donors_orig", "Donors_new"]].rename(
            columns={"Name_new": "Name", "Donors_orig": "Previous Donors", "Donors_new": "New Donors"}
        ).copy()
        changes["New Donors"] = changes["New Donors"].replace("", "(none)")
        changes["Previous Donors"] = changes["Previous Donors"].replace("", "(none)")

        st.session_state.changes_donor = changes
        st.session_state.assets_changes_donor = not changes.empty

        st.subheader("🔍 Review Changes")
        if changes.empty:
            st.success("✅ No changes detected.")
        else:
            st.dataframe(changes)
            if not st.session_state.get("confirm_apply_donor"):
                if st.button("✅ Confirm and Apply Changes", key="donor_confirm"):
                    st.session_state.confirm_apply_donor = True

        # Apply changes
        if st.session_state.assets_changes_donor and st.session_state.confirm_apply_donor:
            total = len(changes)
            success_count = 0
            progress_bar = st.progress(0, text="Initializing update...")

            for i, (_, row) in enumerate(changes.iterrows()):
                new_labels = [] if row["New Donors"] == "(none)" else [l.strip() for l in row["New Donors"].split(",")]
                donor_names = [donor_name_by_label[l] for l in new_labels if l in donor_name_by_label]

                updated_extra_metadata = dict(st.session_state.donor_extra_metadata_by_uid.get(row["UID"], {}))
                updated_extra_metadata["project_donors"] = donor_names

                payload = {
                    "settings": {
                        "extra_metadata": updated_extra_metadata
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
            st.session_state.confirm_apply_donor = False

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