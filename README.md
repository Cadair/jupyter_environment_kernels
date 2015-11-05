Automatic Environment Kernel Detection for Jupyter
==================================================

A Jupyter plugin to enable the automatic detection of environments as kernels.

This plugin will by default look in `~/.virtualenvs` and `~/.conda/envs` for 
the `ipython` executeable to check if IPython / Jupyter is installed. If it 
finds the executeable, it will generate a kernel spec for the environment and 
pass it through to the Notebook.

Install this package in the usual manner then add the following line
to your notebook config file:

    c.NotebookApp.kernel_spec_manager_class = 'environment_kernels.EnvironmentKernelSpecManager'

or run the notebook with the following argument:

    --NotebookApp.kernel_spec_manager_class='environment_kernels.EnvironmentKernelSpecManager'


You can specify which directories to search for kernels by setting the `env_dirs` config:

    --"EnvironmentKernelSpecManager.env_dirs=['/opt/miniconda/envs/']" 

or:

    c.EnvironmentKernelSpecManager.env_dirs=['/opt/miniconda/envs/']


If you want to you can also make it ignore environments with certain names:

    --EnvironmentKernelSpecManager.ignore_envs="['testenv']"

or:

    c.EnvironmentKernelSpecManager.ignore_envs=['testenv']

