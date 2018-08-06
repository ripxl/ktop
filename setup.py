#!/usr/bin/env python
from pathlib import Path
import setuptools
import re


setup_args = dict(
    name="ktop",
    version=re.match(
        r"""__version__\s*=\s*['"](\d+\.\d+\.\d+([abc]\d+)?)['"]""",
        (Path(__file__).parent / "src" / "ktop" / "_version.py").read_text()
    ).groups()[0],
    url="https://github.com/deathbeds/ktop",
    author="Dead Pixels Collective",
    description="Use Jupyter Notebooks and Kernels as Widgets",
    packages=setuptools.find_packages("src"),
    package_dir={"": "src"},
    install_requires=["ipywidgets", "jupyter_client", "nbformat"],
    license="BSD-3-Clause",
    include_package_data=True,
    zip_safe=False,
    keywords="jupyter notebook kernel widget ipywidgets traitlets ipynb",
)

if __name__ == "__main__":
    setuptools.setup(**setup_args)
