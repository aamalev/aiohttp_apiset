import os


def to_name(name):
    name = name.replace('/', '.')
    name = name.replace('{', '')
    name = name.replace('}', '')
    return name


def find_file(file_path: str, search_dirs: list, *,
              base_file: str=None, base_dir: str=None) -> str:
    if file_path.startswith('/'):
        return file_path
    elif file_path.startswith('.'):
        if not base_dir and base_file:
            base_dir = os.path.dirname(base_file)
        if base_dir:
            f = os.path.join(base_dir, file_path)
            return os.path.normpath(f)
    for base_dir in search_dirs:
        f = os.path.join(base_dir, file_path)
        f = os.path.normpath(f)
        if os.path.exists(f):
            return f
    raise FileNotFoundError(file_path)
