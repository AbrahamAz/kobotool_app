import pandas as pd
from .constraint_parser import parse_constraint

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
