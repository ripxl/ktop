from pathlib import Path
from nbformat.v4 import new_notebook, writes, reads


def check_path(file_name):
    """ Safely cast a path within `cwd`
    """
    root = Path(".")
    file_path = (root / "{}.ipynb".format(file_name))
    if root not in file_path.parents:
        raise ValueError("load failed")
    return file_path


def save_notebook(file_name, nb=None, cells=None):
    """ a convenience wrapper around a "safe" notebook save
    """
    if nb is None:
        raise ValueError("filename required")
    file_path = check_path(file_name)

    if nb is None and cells is not None:
        nb = new_notebook()
        nb.cells = list(cells)
    if nb is None:
        raise ValueError("not enough info to save")

    file_path.write_text(writes(nb, split_lines=False))


def load_notebook(file_name):
    """ a convenience wrapper around a "safe" notebook load
    """
    file_path = check_path(file_name)

    if file_path.exists():
        return reads(file_path.read_text())
