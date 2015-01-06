# -*- coding: utf-8 -*-

import os
import glob

from IPython.kernel.kernelspec import KernelSpecManager, KernelSpec, NATIVE_KERNEL_NAME, NoSuchKernel
from IPython.utils.traitlets import List

__all__ = ['EnvironmentKernelSpecManager']

class EnvironmentKernelSpecManager(KernelSpecManager):

    env_dirs = List()
    def _env_dirs_default(self):
        return [os.path.expanduser('~/.virtualenvs/'), os.path.expanduser('~/.conda/envs/')] # We need to add something here!
    
    def _get_env_paths(self):
        return [os.path.join(os.path.expanduser(base_dir), '*/bin/ipython') for base_dir in self.env_dirs]

    def find_python_paths(self):
        # find a python executeable
        python_dirs = {}
        
        for env_path in self._get_env_paths():
            for python_exe in glob.glob(env_path):
                venv_dir = os.path.split(os.path.split(python_exe)[0])[0]
                venv_name = os.path.split(venv_dir)[1]
                python_dirs.update({venv_name: venv_dir})
        
        print(python_dirs)
        return python_dirs
    
    def venv_kernel_specs(self):
        python_dirs = self.find_python_paths()
        kspecs = {}
        for venv_name, venv_dir in python_dirs.items():
            exe_name = os.path.join(venv_dir, 'bin/python')
            kspec_dict =  {"argv": [exe_name,
                                    "-m",
                                    "IPython.kernel",
                                    "-f",
                                    "{connection_file}"],
                           "display_name": "Environment ({})".format(venv_name),
                           "env": {}}

            kspecs.update({venv_name: KernelSpec(**kspec_dict)})
        return kspecs
    
    def find_kernel_specs(self):
        """Returns a dict mapping kernel names to resource directories."""
        d = super(EnvironmentKernelSpecManager, self).find_kernel_specs()
        
        d.update(self.find_python_paths())
        return d

    def get_kernel_spec(self, kernel_name):
        """Returns a :class:`KernelSpec` instance for the given kernel_name.
        
        Raises :exc:`NoSuchKernel` if the given kernel name is not found.
        """
        if kernel_name in {'python', NATIVE_KERNEL_NAME}:
            kspec = KernelSpec(self._native_kernel_resource_dir, **self._native_kernel_dict)
            print(kspec.to_json())
            return kspec

        d = self.find_kernel_specs()
        try:
            resource_dir = d[kernel_name.lower()]
            return KernelSpec.from_resource_dir(resource_dir)
        except FileNotFoundError:
            if kernel_name.lower() in self.venv_kernel_specs():
                return self.venv_kernel_specs()[kernel_name.lower()]
            else:
                raise NoSuchKernel(kernel_name)