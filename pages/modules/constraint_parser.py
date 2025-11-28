import re

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
