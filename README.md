Automatic Environment Kernel Detection for Jupyter
==================================================

A Jupyter plugin to enable the automatic detection of conda environments as kernels.

Install this package in the usual manner then add the following line
to your notebook config file:

    c.NotebookApp.kernel_spec_manager_class = 'environment_kernels.EnvironmentKernelSpecManager'

or run the notebook with the following argument:

   --NotebookApp.kernel_spec_manager_class='environment_kernels.EnvironmentKernelSpecManager'

You can specify which directories to search for kernels by setting the `env_dirs` config:

    --"EnvironmentKernelSpecManager.env_dirs=['/usr/local/packages6/conda/envs/']" 

or:

    c.EnvironmentKernelSpecManager.env_dirs=['/usr/local/packages6/conda/envs/']
