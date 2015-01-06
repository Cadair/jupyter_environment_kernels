Automatic Environment Kernel Detection for Jupyter
==================================================

An Jupyter plugin to enable the automatic detection of conda environments as kernels.

Install this package in the usual manner then add the following line
to your notebook config file:

    c.NotebookApp.kernel_spec_manager_class = 'environment_kernels.EnvironmentKernelSpecManager'

