FROM jupyter/scipy-notebook:400c69639ea5

# handle non-project deps
RUN conda install -y -n root git

# contains everything it reliably can
COPY environment-dev.yml /home/jovyan/ktop/environment-dev.yml
RUN conda env update --quiet \
    -n root \
    --file /home/jovyan/ktop/environment-dev.yml \
  && conda clean -tipsy \
  && conda list

# install things with demonstrated install weirdness
COPY environment-jupyter.yml /home/jovyan/ktop/environment-jupyter.yml
RUN conda env update --quiet \
    -n root \
    --file /home/jovyan/ktop/environment-jupyter.yml \
  && conda clean -tipsy \
  && conda list

# handle extension things
RUN set -ex \
  && jupyter nbextension install rise --py --sys-prefix \
  && jupyter nbextension enable rise --py --sys-prefix

# do this to get the nodejs toolchain
RUN jupyter lab build

# install and validate labextensions
RUN set -ex \
  && jupyter labextension install --no-build \
    @jupyterlab/hub-extension \
  && jupyter labextension install --no-build \
    @jupyter-widgets/jupyterlab-manager \
  && jupyter labextension install --no-build \
    bqplot

RUN jupyter lab build \
  && jupyter labextension list

# copy in user's stuff
COPY [ \
  "LICENSE", \
  "MANIFEST.in", \
  "README.md", \
  "setup.py", \
  "/home/jovyan/ktop/" \
]

COPY [ \
  "src/", \
  "/home/jovyan/ktop/src" \
]

COPY  [ \
  "conda.recipe/", \
  "/home/jovyan/ktop/conda.recipe" \
]

# fix permissions
USER root
RUN chown -R ${NB_UID} ${HOME}

# switch back to normal user
USER ${NB_USER}

# attempt build and install local conda package
RUN cd /home/jovyan/ktop && \
  conda-build -c conda-forge conda.recipe
RUN cd /home/jovyan/ktop \
  && conda install --use-local -c conda-forge ktop \
  || python setup.py develop

# add the notebooks
COPY [ \
  "notebooks", \
  "/home/jovyan/notebooks" \
]

# fix permissions
USER root
RUN chown -R ${NB_UID} ${HOME}/notebooks

# switch back to normal user
USER ${NB_USER}
