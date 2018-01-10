from pathlib import Path
from nbformat.v4 import new_notebook, writes


def save_notebook(file_name, nb=None, cells=None):
    if nb is None:
        raise ValueError("filename required")
    root = Path(".")
    file_path = (root / "{}.ipynb".format(file_name))
    if root not in file_path.parents:
        raise ValueError("save failed")
    else:
        if nb is None and cells is not None:
            nb = new_notebook()
            nb.cells = list(cells)
        if nb is None:
            raise ValueError("not enough info to save")
        file_path.write_text(writes(nb, split_lines=False))
