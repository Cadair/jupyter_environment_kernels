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


## Customization

You can specify which directories to search for kernels by setting the 
`env_dirs` config in the configuration file:

    c.EnvironmentKernelSpecManager.env_dirs=['/opt/miniconda/envs/']

or by appending the following argument when running a notebook server:

    --"EnvironmentKernelSpecManager.env_dirs=['/opt/miniconda/envs/']" 


If you want to you can also make it ignore environments with certain names:

    c.EnvironmentKernelSpecManager.blacklist_envs=['testenv']

or:

    --EnvironmentKernelSpecManager.blacklist_envs="['testenv']"

Or you can specify a whitelist of "allowed" environments with:

    c.EnvironmentKernelSpecManager.whitelist_envs=['testenv']

or:

    --EnvironmentKernelSpecManager.whitelist_envs="['testenv']"

