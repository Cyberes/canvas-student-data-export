import os
import string


def make_valid_filename(input_str):
    if not input_str:
        return input_str

    # Make sure we have a string and not PosixPath
    input_str = str(input_str)

    # Remove invalid characters
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    input_str = input_str.replace("+", " ")  # Canvas default for spaces
    input_str = input_str.replace(":", "-")
    input_str = input_str.replace("/", "-")
    input_str = "".join(c for c in input_str if c in valid_chars)

    # Remove leading and trailing whitespace
    input_str = input_str.lstrip().rstrip()

    # Remove trailing periods
    input_str = input_str.rstrip(".")

    return input_str


def make_valid_folder_path(input_str):
    input_str = str(input_str)
    # Remove invalid characters
    valid_chars = "-_.()/ %s%s" % (string.ascii_letters, string.digits)
    input_str = input_str.replace("+", " ")  # Canvas default for spaces
    input_str = input_str.replace(":", "-")
    input_str = "".join(c for c in input_str if c in valid_chars)

    # Remove leading and trailing whitespace, separators
    input_str = input_str.lstrip().rstrip().strip("/").strip("\\")

    # Remove trailing periods
    input_str = input_str.rstrip(".")

    # Replace path separators with OS default
    input_str = input_str.replace("/", os.sep)

    return input_str


def shorten_file_name(input_string, shorten_by) -> str:
    if not input_string or shorten_by <= 0:
        return input_string
    input_string = str(input_string)

    # Shorten string by specified value + 1 for "-" to indicate incomplete file name (trailing periods not allowed)
    input_string = input_string[:len(input_string) - (shorten_by + 1)]

    input_string = input_string.rstrip().rstrip(".").rstrip("-")
    input_string += "-"

    return input_string
