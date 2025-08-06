import pandas as pd

def name2label_questions(tool_survey: pd.DataFrame, tool_choices: pd.DataFrame, col: str, label: str) -> str:
    # For each column check if it is a select_multiple
    if "/" in col:
        parts = col.split("/")
        q_name = parts[0]
        c_name = ".".join(parts[1:])
    else:
        q_name = col
        c_name = None
    
    # Find question in survey sheet
    if q_name in tool_survey["name"].values:
        q_row = tool_survey[tool_survey["name"] == q_name].iloc[0]
        q_label = q_row.get(label, q_name)

        if q_label is None or q_row.get('type') == "note":
            q_label = q_name
        
        if c_name:
            list_name = q_row.get("list_name")
            if list_name is None or str(list_name).lower() == 'na':
                list_name = None

            if list_name:
                matches = tool_choices[
                    (tool_choices['list_name'] == list_name) and
                    (tool_choices['name'] == c_name)
                ]

                if not matches.empty:
                    c_label = matches.iloc[0].get(label)
                else:
                    c_label = None
            else:
                c_label = None
        else:
            c_label = None

        label = f"{q_label}/{c_label}" if c_label else q_label

    else:
        label = q_name

    return label


def name2label_choices_one(tool_survey: pd.DataFrame,
                           tool_choices: pd.DataFrame,
                           label: str,
                           data: pd.DataFrame,
                           col: str) -> pd.Series:
    # Get all the types of the questions 
    q_list_name = tool_survey.loc[tool_survey['name'] == col, 'list_name']

    if q_list_name.empty:
        return pd.Series([None] * len(data), name = col)
    
    relevant_choices = tool_choices[tool_choices['list_name'] == q_list_name][["name", label]]

    data_col = data[[col]].copy()
    data_col = data_col.rename(columns={col: 'col'})
    merged = data_col.merge(relevant_choices, how='left', left_on='col', right_on='name')

    return merged[label]


    