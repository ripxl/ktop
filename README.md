# ktop
> Treat Multiple Notebooks and Kernels like code

`ktop` gives you reactive Notebooks and Kernels :
- create, open, and save notebooks on-the-fly in memory, or on disk
- modify and execute cells in one or more kernels
- react to conditions in running kernels
- view and link to remote Widgets

# Installation
> TBD

# developing
```
git clone https://github.com/ripxl/ktop
cd ktop
conda env update -v --file environment-dev.yml
conda env update -v --file environment-jupyter.yml
source activate ktop-dev
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
