import pandas as pd
from io import BytesIO

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
