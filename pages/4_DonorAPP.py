import os
import streamlit as st
from databricks import sql
from typing import List, Tuple

#-----CONFIG-----

HOSTNAME = st.secrets["DBX_HOSTNAME"]
HTTP_PATH = st.secrets["DBX_HTTP_PATH"]
CATALOG = st.secrets["DBX_CATALOG"]
PROJECT_SCHEMA = st.secrets["DBX_PROJECT_SCHEMA"]
ASSET_SCHEMA = st.secrets["DBX_ASSET_SCHEMA"]

ACCESS_TOKEN = st.secrets["DBX_ACCESS_TOKEN"]

st.set_page_config(page_title= "Project to Asset Linker",
                   page_icon="🔗",
                   layout="wide")

#-----DB HELPER-----
@st.cache_data(show_spinner=False, ttl=60)
def get_assets() -> List[Tuple[str,str]]:
    q = f"SELECT uid, name FROM {CATALOG}.kobo_gold.asset ORDER BY name"
    return run_query_fetchall(q)

@st.cache_data(show_spinner=False, ttl=60)
def get_projects() -> List[Tuple[str,str]]:
    q = f"SELECT ProjectId, ProjectName FROM {CATALOG}.{PROJECT_SCHEMA}.project ORDER BY ProjectName"
    return run_query_fetchall(q)

@st.cache_data(show_spinner=False, ttl=15)
def get_existing_links(asset_uid: str) -> List[Tuple[str]]:
    q = f"""
        SELECT ProjectId
        FROM {CATALOG}.{ASSET_SCHEMA}.asset_dynprojectID
        WHERE asset_uid = ?
        ORDER BY project_id
        """
    return run_query_fetchall(q, (asset_uid,))

def merge_rollup(asset_uid: str):
    q = f"""
        MERGE INTO {CATALOG}.{ASSET_SCHEMA}.donorAsset t
        USING (
            SELECT ? AS asset_uid,
                collect_set(project_id) AS project_ids,
                current_timestamp() AS update_at
            FROM {CATALOG}.{ASSET_SCHEMA}.asset_dynprojectID
            WHERE asset_uid = ?
        ) s
        on t.asset_uid = s.asset_uid
        WHEN MATCHED THEN UPDATE SET t.project_ids = s.project_ids, t.updated_at = s.updated_at
        WHEN NOT MATCHED THEN INSERT (asset_uid, project_ids, updated_at) VALUE (s.asset_uid, s.project_ids, s.updated_at)
        """
    run_exec(q, (asset_uid, asset_uid))


def upsert_links(asset_uid: str, project_ids: List[str], linked_by: str, replace_mode: bool):
    if replace_mode:
        del_q = f"DELETE FROM {CATALOG}.{ASSET_SCHEMA}.asset_dynprojectID WHERE asset_uid = ?"
        run_exec(del_q)

    if project_ids:
        current = {pid for (pid,) in get_existing_links(asset_uid)}
        to_insert = [pid for pid in project_ids if pid not in current] if not replace_mode else project_ids

        ins_q = f"""
                INSERT INTO {CATALOG}.{ASSET_SCHEMA}.asset_dynprojectID (asset_uid, project_id, updated_at)
                VALUES (?,?,?)
                """
        for pid in to_insert:
            run_exec(ins_q, (asset_uid, pid, linked_by))

    merge_rollup(asset_uid)

def run_query_fetchall(query: str, params: Tuple = None):
    with connect_db() as conn, conn.cursor() as cur:
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        return cur.fetchall()
    
def run_exec(query: str, params: Tuple = None):
    with connect_db() as conn, conn.cursor() as cur:
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)

def connect_db():
    if ACCESS_TOKEN:
        return sql.connect(server_hostname = HOSTNAME, http_path = HTTP_PATH,
                           access_token = ACCESS_TOKEN)
    
    raise RuntimeError("No Databricks auth configure. Set DBX_ACCESS_TOKEN or AAD SECRETS")

st.title("🔗 Project ↔ Asset Linker")
st.caption("Map multiple projects to one asset and keep donor roll-ups up to date.")

assets = get_assets()

projects = get_projects()

if not assets:
    st.error("No assets found. Check your catalog/schema or permissions.")
    st.stop()
if not projects:
    st.error("No projects found. Check your catalog/schema or permissions.")
    st.stop()

col1, col2 = st.columns(2)

with col1:
    asset_display = [f"{name} - {uid}" for uid, name in assets]
    choice_idx = st.selectbox("Choose an asset", options = range(len(assets)),
                              format_func=lambda i: asset_display[i])
    asset_uid = assets[choice_idx][0]
    st.write(f"**Selected Asset UID:** `{asset_uid}`")

    existing = [pid for (pid,) in get_existing_links(asset_uid)]
    st.info(f"Currently linked projects: {', '.join(existing) if existing else 'none'}")

with col2:
    proj_display = [f"{pname} - {pid}" for pid, name in projects]
    proj_ids = [pid for pid, _ in projects]
    display_to_id = {f"{pname} - {pid}": pid for pid, pname in projects}

    default_sel = [f"{pname} - {pid}" for pid, pname in projects if pid in existing]
    selection = st.multiselect("Select projcet to link", options = proj_display,
                               default=default_sel)
    select_ids = [display_to_id[s] for s in selection]

st.divider()
replace_mode = st.checkbox("Replace existing links for this asset (delete then insert)", value = False,
                           help="Checked: overwrite all links to match your selection. Unchecked: append only new links")

user_email = st.text_input("Your email (for audit)", value="", placeholder="fname.lname@drc.ngo")
go = st.button("Save links", type="primary")

if go:
    if not user_email:
        st.warning("Please enter your email for audit.")
        st.stop()
    try:
        upsert_links(asset_uid,select_ids, user_email, replace_mode)
        st.success(f"Saved links for asset `{asset_uid}`. Total selected: {len(select_ids)}")

        get_existing_links.clear()
        st.rerun()
    except Exception as e:
        st.exception(e)

st.subheader("Donor roll‑up preview")
try:
    q = f"SELECT asset_uid, project_ids, updated_at FROM {CATALOG}.{ASSET_SCHEMA}.donorAsset where asset_uid = ?"
    row = run_query_fetchall(q, (asset_uid,))
    if row:
        asset_uid_r, project_ids_r, update_at_r = row[0]
        st.write({"asset_uid": asset_uid_r, "project_ids": project_ids_r, "updated_at": str(update_at_r)})
    else:
        st.write("No Donor Asset row yet.")
except Exception as e:
    st.warning(f"Could not read donorAsset: {e}")