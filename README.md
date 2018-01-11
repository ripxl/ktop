# ipynotebookwidget
> Treat Multiple Notebooks and Kernels like code

`ipynotebookwidget` gives you reactive Notebooks and Kernels :
- create, open, and save notebooks on-the-fly in memory, or on disk
- modify and execute cells in one or more kernels
- react to conditions in running kernels
- view and link to remote Widgets

# Installation
```
git clone https://github.com/ripxl/ipynotebookwidget
cd ipynotebookwidget
conda env update -v
conda env update -v --file environment-jupyter.yml
source activate notebook-widget
python setup.py develop
# for now, to ensure a working jupyterlab with widgets
jupyter labextension install @jupyter-widgets/jupyterlab-manager
jupyter labextension install bqplot
```

# API
## `Notebook`
### `run([cells=None])`
### `save()`

## `Kernel`
### `view(widget=DefaultKernelView)`
### `save()`
