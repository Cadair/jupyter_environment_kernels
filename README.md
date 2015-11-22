Automatic Environment Kernel Detection for Jupyter
==================================================

A Jupyter plugin to enable the automatic detection of environments as kernels.

This plugin looks in the directories you specify for installed environments
which have Jupyter installed and lists them as kernels for Jupyter to find.
This makes it easy to run one notebook instance and access kernels with access
to different versions of Python or different modules seamlessly.


## Installation

The plugin can be installed with:

    pip install environment_kernels

To enable the plugin add the following line to your notebook [config file](https://jupyter-notebook.readthedocs.org/en/latest/config.html):

    c.NotebookApp.kernel_spec_manager_class = 'environment_kernels.EnvironmentKernelSpecManager'

to create a config file run:

    jupyter notebook --generate-config

or run the notebook with the following argument:

    --NotebookApp.kernel_spec_manager_class='environment_kernels.EnvironmentKernelSpecManager'


## Search Directories for Environments

The plugin works by searching a set of directories for subdriectories which are
environments with the following pattern on Linux and OS/X:
    
    BASE_DIR/ENV_NAME/bin/ipython

and on Windows::

    BASE_DIR\ENV_NAME\Scripts\ipython

The default base directories are `~/.conda/envs`, `~/.virtualenvs` and if the
jupyter notebook is being run in the root environment `conda.config.envs_dirs` 
will be imported added to the search path, if the notebook server is run from
inside a conda environment then the `CONDA_ENV_DIR` variable will be set and
the section of the path before `/env/` will be added to the search list.
You can add extra directories to the search path by using the
`extra_env_dirs` config:

    c.EnvironmentKernelSpecManager.extra_env_dirs=['/opt/miniconda/envs/']

or all the automatic behavior can be overriddenby setting the `env_dirs`
config:

    c.EnvironmentKernelSpecManager.env_dirs=['/opt/miniconda/envs/']

## Limiting Environments

If you want to you can also make it ignore environments with certain names:

    c.EnvironmentKernelSpecManager.blacklist_envs=['testenv']

or:

    --EnvironmentKernelSpecManager.blacklist_envs="['testenv']"

Or you can specify a whitelist of "allowed" environments with:

    c.EnvironmentKernelSpecManager.whitelist_envs=['testenv']

or:

    --EnvironmentKernelSpecManager.whitelist_envs="['testenv']"

