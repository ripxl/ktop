# ktop
> Use Jupyter Notebooks and Kernels as Widgets

`ktop` gives you reactive Notebooks and Kernels:
- create, open, and save notebooks on-the-fly in memory, or on disk
- modify and execute cells in one or more kernels
- react to conditions in running kernels
- view and link to remote Widgets

# Installation
> TBD

# Usage
## Run a notebook.
```python
import ktop
nb = ktop.Notebook()
nb.nbformat.cells = ktop.Code("print('hello world')")
k = nb.run_one()
# ... wait a while
print(k.nbformat.cells[0].outputs)
```

## Run a couple kernels
```python
for world in "☿♀🜨♂♃♄⛢♆":
    k = nb.run_one()
    k.nbformat.cells[0].source = f"print('hello {world}')"
# ... wait a while
for k in nb.kernels:
    print(k.nbformat.cells[0].outputs)
```

# Developing
```
git clone https://github.com/deathbeds/ktop
conda env update
source activate ktop-demo
bash postBuild
```
