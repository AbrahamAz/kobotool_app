import pandas as pd
def name2label_questions(survey: pd.DataFrame, 
                         choices: pd.DataFrame, 
                         col: str, 
                         label: str) -> str:
    # For each column check if it is a select_multiple
    if "/" in col:
        parts = col.split("/")
        q_name = parts[0]
        c_name = ".".join(parts[1:])
    else:
        q_name = col
        c_name = None
    
    # Find question in survey sheet
    if q_name in survey["name"].values:
        q_row = survey[survey["name"] == q_name].iloc[0]
        q_label = q_row.get(label, q_name)

        if q_label is None or q_row.get('type') == "note":
            q_label = q_name
        
        if c_name:
            list_name = q_row.get("list_name")
            if list_name is None or str(list_name).lower() == 'na':
                list_name = None

            if list_name:
                matches = choices[
                    (choices['list_name'] == list_name) & 
                    (choices['name'] == c_name)
                ]

                if not matches.empty:
                    c_label = matches.iloc[0].get(label)
                else:
                    c_label = None
            else:
                c_label = None
        else:
            c_label = None

        final_label = f"{q_label}/{c_label}" if c_label else q_label

    else:
        final_label = q_name

    return final_label


def name2label_choices_one(survey: pd.DataFrame,
                           choices: pd.DataFrame,
                           label: str,
                           data: pd.DataFrame,
                           col: str) -> pd.Series:
    # get the list_name of the specific question
    q_list_name_series  = survey.loc[survey['name'] == col,'list_name']
    if q_list_name_series.empty:
        return pd.Series([None] * len(data), name = col)
    
    q_list_name = q_list_name_series.iloc[0] 

    # get the relevant choices 
    relevant_choices = choices.loc[choices['list_name'] == q_list_name,["name", label]]
    data_col = data[[col]].copy()
    data_col = data_col.rename(columns={col: 'col'})
    merged = data_col.merge(relevant_choices, how='left', left_on='col', right_on='name')

    return merged[label]

def name2label_choices_multiple(survey: pd.DataFrame,
                                choices: pd.DataFrame,
                                data: pd.DataFrame,
                                col: str,
                                label:str,
                                sep: str) -> pd.Series:
    # get all the columns that belong to this select_multiple group
    col_internal = [c for c in data.columns if f"{col}{sep}" in c]

    if not col_internal:
        return pd.Series([None] * len(data), name = col)
    
    # copy a subset of the relevant columns 
    d_join = data[col_internal].copy()

    for col_name in col_internal:
        # extract the xml value from the column (e.g., 'water_source/piped' -> 'piped')
        xml_answer = col_name.split(sep, 1)[1]

        # replace "1" with xml_answer, else NaN
        d_join[col_name] = d_join[col_name].apply(lambda x: xml_answer if str(x).strip() in ["1", "1.0", "True", "true"] else None)
        # get the list_name from this group
        base_question = col_name.split(sep, 1)[0]
        match = survey.loc[survey['name'] == base_question, 'list_name']
        if match.empty:
            continue
        list_name = match.iloc[0]

        # get the relevant choices
        t_choices = choices[choices['list_name'] == list_name][['name', label]]

        # merge to replace xml_answers with labels
        d_col = pd.DataFrame({'col': d_join[col_name]})
        d_merged = d_col.merge(t_choices, how = 'left', left_on='col', right_on='name')[[label]]
        d_join[col_name] = d_merged[label]

    merged = d_join.apply(lambda row: ';'.join(filter(None, row.dropna().astype(str))), axis=1)

    return merged

