def read_data_from_file(file_path, separator):
    """
    Read data from a text file using the specified separator.

    :param file_path: The path to the text file.
    :param separator: The separator used to split the data.
    :return: A list of data elements.
    """
    try:
        with open(file_path, 'r') as file:
            data = file.read()
            elements = data.split(separator)
        filtered_elements = [el for el in elements if el != '']
        return filtered_elements

    except FileNotFoundError:
        print(f"File not found: {file_path}")

    except Exception as e:
        pass