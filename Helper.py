import re

def human_readable_to_long(human_readable_num_str: str) -> float:
    """
    Converts a human-readable number string (e.g., "10k", "5.5M", "1B")
    into its full numerical (float) equivalent.

    Args:
        human_readable_num_str (str): The string representing the human-readable number.
                                      Expected formats: "123", "10k", "1.5M", "0.7B", etc.
                                      Suffixes can be 'k', 'm', 'b', 't' (case-insensitive).

    Returns:
        float: The full numerical value as a float.

    Raises:
        ValueError: If the input string format is not recognized.
    """
    if not isinstance(human_readable_num_str, str):
        raise TypeError("Input must be a string.")

    # Clean and normalize the input string (remove leading/trailing whitespace, convert to lowercase)
    s = human_readable_num_str.strip().lower()

    # Regex to capture the numeric part and the optional suffix
    # Group 1: The numeric part (e.g., "10", "1.5") - handles integers and decimals
    # Group 2: The optional suffix (k, m, b, t)
    match = re.fullmatch(r"(\d+(?:\.\d+)?)([kmbt])?", s)

    if not match:
        raise ValueError(f"Invalid human-readable number format: '{human_readable_num_str}'")

    number_part_str = match.group(1)
    suffix = match.group(2) # This will be None if no suffix was found

    try:
        value = float(number_part_str)
    except ValueError:
        # This case should ideally be covered by the regex, but good for robustness
        raise ValueError(f"Could not parse numeric part '{number_part_str}' from '{human_readable_num_str}'")

    multipliers = {
        'k': 1_000,
        'm': 1_000_000
    }

    if suffix:
        value *= multipliers.get(suffix, 1) # If suffix is not in multipliers (shouldn't happen with current regex), default to 1

    return value