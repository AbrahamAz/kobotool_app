import json
import requests




def fetch_kobo_form(kobo_id: str, api_token_file, output_path: str) -> None:
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
        try:
            api_token = json.load(api_token_file)
            if "token" not in api_token:
                raise ValueError("The JSON file must contain a 'token' key.")
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON file. Please upload a properly formatted JSON file.")

        headers = {"Authorization": f"Token {api_token['token']}"}
        # Fetch the asset metadata to get the correct XLSForm download URL
        asset_url = f"https://kobo.drc.ngo/api/v2/assets/{kobo_id}.json"
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
