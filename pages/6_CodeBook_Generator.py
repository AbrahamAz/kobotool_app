import streamlit as st
import json
import requests
import pandas as pd
from io import BytesIO
import os
import re


# Set the page layout to wide
st.set_page_config(layout="wide")

# Ensure the 'data' directory exists
if not os.path.exists("data"):
    os.makedirs("data")

    
def parse_constraint(constraint: str, data_type: str) -> str:
    """
    Parse constraints based on data type and return human-readable format.
    
    Args:
        constraint (str): The constraint string from Kobo form
        data_type (str): The type of the variable
        
    Returns:
        str: Human-readable constraint
    """
    if not constraint:
        return None
        
    # For numeric types
    if any(t in data_type.lower() for t in ['integer', 'decimal', 'number']):
        return parse_numeric_constraint(constraint)
    
    # For now, return None for other types
    # TODO: Add support for other constraint types (regex, etc.)
    return None


def extract_variables_from_excel(file_path: str) -> pd.DataFrame:
    """
    Extract variables from a Kobo form Excel file, including multilingual labels and category values.
    Handles missing or empty 'choices' sheet gracefully.

    Args:
        file_path (str): The path to the Excel file.

    Returns:
        pd.DataFrame: A DataFrame containing variable names, English labels, data types, and category values with multilingual labels.
    """
    # Try to load both 'survey' and 'choices' sheets from the Excel file
    try:
        xls = pd.ExcelFile(file_path)
        if 'survey' not in xls.sheet_names:
            return pd.DataFrame()  # No survey sheet, return empty
        survey_df = pd.read_excel(xls, sheet_name="survey")
        if 'choices' in xls.sheet_names:
            choices_df = pd.read_excel(xls, sheet_name="choices")
        else:
            choices_df = None
    except Exception:
        return pd.DataFrame()  # If file is not a valid Excel, return empty

    variables = []

    # Determine the primary label column
    available_languages = [col for col in survey_df.columns if col.startswith("label")]
    primary_label_column = None

    if len(available_languages) == 1:
        # If only one language is available, use it as the primary label column
        primary_label_column = available_languages[0]
    elif "label::english" in available_languages:
        # If multiple languages are available, prioritize 'label::english'
        primary_label_column = "label::english"
    else:
        # Fallback to the first available language
        primary_label_column = available_languages[0] if available_languages else None

    for _, row in survey_df.iterrows():
        label = row.get(primary_label_column, None) if primary_label_column else None
        category_values = None
        allowed_values = None

        # Extract allowed values from constraints if present
        if "constraint" in row and pd.notna(row["constraint"]):
            allowed_values = parse_constraint(row["constraint"], row["type"])

        if (choices_df is not None and (row["type"].startswith("select_one") or row["type"].startswith("select_multiple"))):
            list_name = row["type"].split(" ")[1] if " " in row["type"] else None
            if list_name:
                category_values = choices_df[choices_df["list_name"] == list_name]["name"].tolist()
                if category_values:
                    allowed_values = ", ".join(category_values)

        variables.append({
            "name": row["name"],
            primary_label_column: label,  # Use the determined primary label column
            "type": map_data_type(row["type"]),
            "categories": category_values,
            "allowed_values": allowed_values
        })

    variables_df = pd.DataFrame(variables)
    return variables_df

def map_data_type(data_type: str) -> str:
    """
    Map Kobo data types to human-readable categories.

    Args:
        data_type (str): The Kobo data type.

    Returns:
        str: A human-readable category.
    """
    if data_type.startswith("select_one"):
        return "Categorical variable"
    elif data_type.startswith("select_multiple"):
        return "Multiple-choice Categorical variable"
    elif data_type in ["start", "end"]:
        return "date"
    else:
        return data_type  # Keep the original type for all other cases

def parse_numeric_constraint(constraint: str) -> str:
    """
    Parse numeric constraints from Kobo Excel form and convert them to human-readable format.
    
    Args:
        constraint (str): The constraint string from Kobo form (e.g., '.>=18 and .<=80')
    
    Returns:
        str: Human-readable constraint (e.g., '[18 - 80]' or '≥ 18' or 'Between 18 and 80')
    """
    if not constraint or not isinstance(constraint, str):
        return None

    # Clean up the constraint string
    constraint = constraint.replace(" ", "")
    
    # Common patterns for numeric constraints
    greater_than = re.search(r'\.>(\d+)', constraint)
    greater_equal = re.search(r'\.>=(\d+)', constraint)
    less_than = re.search(r'\.<(\d+)', constraint)
    less_equal = re.search(r'\.<=(\d+)', constraint)
    equals = re.search(r'\.=(\d+)', constraint)
    
    # Check for range (both upper and lower bounds)
    if ('and' in constraint):
        # Extract bounds
        lower_bound = greater_equal.group(1) if greater_equal else (
            int(greater_than.group(1)) + 1 if greater_than else None)
        upper_bound = less_equal.group(1) if less_equal else (
            int(less_than.group(1)) - 1 if less_than else None)
        
        if lower_bound and upper_bound:
            return f"[{lower_bound} - {upper_bound}]"
        elif lower_bound:
            return f"≥ {lower_bound}"
        elif upper_bound:
            return f"≤ {upper_bound}"
    
    # Single conditions
    elif greater_equal:
        return f"≥ {greater_equal.group(1)}"
    elif greater_than:
        return f"> {greater_than.group(1)}"
    elif less_equal:
        return f"≤ {less_equal.group(1)}"
    elif less_than:
        return f"< {less_than.group(1)}"
    elif equals:
        return f"= {equals.group(1)}"
    
    return None


def handle_file_upload(uploaded_file) -> pd.DataFrame:
    """
    Handle the uploaded Excel file and convert it to a DataFrame.

    Args:
        uploaded_file: The uploaded Excel file.

    Returns:
        pd.DataFrame: The content of the Excel file as a DataFrame.
    """
    try:
        excel_data = pd.read_excel(BytesIO(uploaded_file.read()))
        return excel_data
    except Exception as e:
        raise ValueError(f"Failed to process the uploaded file: {e}")
    
def fetch_kobo_form(kobo_id: str, owner_token, output_path: str) -> None:
    """
    Fetch a Kobo form Excel file using the Kobo API and save it locally.

    Args:
        kobo_id (str): The ID of the Kobo form.
        api_token_file: The uploaded JSON file containing the API token.
        output_path (str): The local path to save the downloaded Excel file.

    Returns:
        None
    """
    try:
        # Validate and load the API token

        headers = {"Authorization": f"Token {owner_token}"}
        # Fetch the asset metadata to get the correct XLSForm download URL
        asset_url = f"{st.session_state.kobo_url}/api/v2/assets/{kobo_id}.json"
        response = requests.get(asset_url, headers=headers)

        if response.status_code != 200:
            response.raise_for_status()

        asset = response.json()
        xlsform_url = next((d.get("url") for d in asset.get("downloads", []) if d.get("format") == "xls"), None)

        if not xlsform_url:
            raise ValueError("XLSForm download URL not found in asset metadata.")

        # Download the XLSForm
        response = requests.get(xlsform_url, headers=headers, stream=True)

        if response.status_code == 200:
            with open(output_path, "wb") as excel_file:
                for chunk in response.iter_content(chunk_size=1024):
                    excel_file.write(chunk)
        else:
            response.raise_for_status()
    except Exception as e:
        raise ValueError(f"Failed to fetch Kobo form: {e}")


def main():
    """
    Main function to run the Streamlit app.
    """
    st.title("Codebook Generator (Impact Initiatives)")

    for key in ["owner_token", "owner_username","headers_owner", "kobo_url"]:
        if key not in st.session_state:
            st.session_state[key] = None

    kobo_url = st.sidebar.text_input("Please enter the kobo url", value ="https://kobo.drc.ngo")
    st.session_state.kobo_url = kobo_url

    CONFIG = {
        "API_ROOT": f"{st.session_state.kobo_url}/api/v2"
    }
        
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

        if selected_asset_display and st.session_state.owner_token:
            with st.spinner("Fetching form data..."):
                output_path = "data/fetched_form.xlsx"  # Define a path to save the Excel file
                fetch_kobo_form(asset_uid, st.session_state.owner_token, output_path)

            success_msg = st.success("Form fetched successfully!", icon="✅")
            success_msg.empty()

            # Extract variables from the downloaded Excel file
            variables_df = extract_variables_from_excel(output_path)
            success_msg2 = st.success("Variables extracted successfully!", icon="✅")
            success_msg2.empty()
            st.dataframe(variables_df, use_container_width=True)

            # Provide download option
            csv = variables_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Variables as CSV",
                data=csv,
                file_name="variables.csv",
                mime="text/csv"
            )

        else:
            st.error("Please provide both Kobo Form ID and API Token.")


if __name__ == "__main__":
    main()
