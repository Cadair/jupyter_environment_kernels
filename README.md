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

To create a config file run:

    jupyter notebook --generate-config

or run the notebook with the following argument:

    --NotebookApp.kernel_spec_manager_class='environment_kernels.EnvironmentKernelSpecManager'

## Search Directories for Environments

The plugin works by getting a list of possible environments which might contain an
ipython kernel.

There are multiple ways to find possible environments:

* All subdirs of the base directories (default: `~/.conda/envs` for conda
  based environments and `~/.virtualenvs`) for virtualenv based environments.
* If the jupyter notebook is being run in the conda root environment
  `conda.config.envs_dirs` will be imported and all subdirs of these
  dirs will be added to the list of possible environments.
* If the notebook server is run from inside a conda environment then the
  `CONDA_ENV_DIR` variable will be set and will be used to find the
  directory which contains the environments.
* If a `conda` executeable is available, it will be queried for a list
  of environments.

Each possible environment will be searched for an `ipython` executeable and
if found, a kernel entry will be added on the fly.

The ipython search pattern is on Linux and OS/X:

    ENV_NAME/{bin|Scripts}/ipython

and on Windows:

    ENV_NAME\{bin|Scripts}\ipython.exe

The kernels will be named after the type (conda or virtualenv) and by the
name of the environment directory (example: the kernel in conda environment
`C:\miniconda\envs\tests` gets the name `conda_tests`). If there are multiple
envs which would result in the same kernel name (e.g. when multiple base dirs
are configured, which each contain an environment with the same name), only the
first kernel will be used and this ommision will be mentioned in the notebook 
console log.

You can configure this behaviour in mutliple ways:

You can override the default base directories by setting the following
config values:

    c.EnvironmentKernelSpecManager.virtualenv_env_dirs=['/opt/virtualenv/envs/']
    c.EnvironmentKernelSpecManager.conda_env_dirs=['/opt/miniconda/envs/']

You can also disable specific search paths:

    c.EnvironmentKernelSpecManager.find_conda_envs=False
    c.EnvironmentKernelSpecManager.find_virtualenv_envs=False

The above disables both types of environments, so this will effectivly 
disable all environment kernels.

You can also disable only the conda call, which is expensive but the only reliable way
on windows:

    c.EnvironmentKernelSpecManager.use_conda_directly=False

## Limiting Environments

If you want to, you can also ignore environments with certain names:

    c.EnvironmentKernelSpecManager.blacklist_envs=['conda_testenv']

Or you can specify a whitelist of "allowed" environments with:

    c.EnvironmentKernelSpecManager.whitelist_envs=['virtualenv_testenv']

## Configuring the display name

The default lists all environmental kernels as `Environment (type_name)`. This
can be cumbersome, as these kernels are usually sorted higher than other kernels.

You can change the display name via this config (you must include the
placeholder `{}`!):

    c.EnvironmentKernelSpecManager.display_name_template="~Env ({})"

## Config via the commandline

All config values can also be set on the commandline by using the config value as argument:

As an example:

    c.EnvironmentKernelSpecManager.blacklist_envs=['conda_testenv']

becomes

    --EnvironmentKernelSpecManager.blacklist_envs="['conda_testenv']"
