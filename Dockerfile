FROM jupyter/scipy-notebook:400c69639ea5

# handle non-project deps
RUN conda install -n root git

# contains everything it reliably can
COPY environment-dev.yml /home/jovyan/environment-dev.yml
RUN conda env update --quiet \
    -n root \
    --file /home/jovyan/environment-dev.yml \
  && conda clean -tipsy \
  && conda list

# install things with demonstrated install weirdness
COPY environment-jupyter.yml /home/jovyan/environment-jupyter.yml
RUN conda env update --quiet \
    -n root \
    --file /home/jovyan/environment-jupyter.yml \
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
  && jupyter labextension install  --no-build \
     @jupyter-widgets/jupyterlab-manager \
  && jupyter labextension install --no-build \
     bqplot \
  && jupyter lab build \
  && jupyter labextension list

# copy in user's stuff
COPY . ${HOME}

# fix permissions
USER root
RUN chown -R ${NB_UID} ${HOME}

# switch back to normal user
USER ${NB_USER}

# build and install local conda package
RUN (conda build -c conda-forge conda.recipe \
    && conda install --use-local -c conda-forge \
      ktop \
    && conda clean -tipsy \
    && conda list \
    && mkdir -p /home/jovyan/conda.channel/noarch \
    && cp -r /opt/conda/conda-bld/noarch/* /home/jovyan/conda.channel/noarch/) \
  || python setup.py develop
