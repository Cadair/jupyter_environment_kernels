# -*- coding: utf-8 -*-
"""
Created on Tue Nov 18 16:01:32 2014

@author: stuart
"""
import os
import io
import glob

from IPython.kernel.kernelspec import KernelSpecManager, KernelSpec, NATIVE_KERNEL_NAME, NoSuchKernel
from IPython.utils.traitlets import Unicode

class CondaEnvKernelSpecManager(KernelSpecManager):

    virtual_env_root = Unicode()
    def _virtual_env_root_default(self):
        return os.path.expanduser('/usr/local/packages6/conda/envs/')

    def find_kernel_paths(self):
        # find a python executeable
        python_dirs = {}
        for python_exe in glob.glob(os.path.join(self.virtual_env_root, '*/bin/ipython')):
            venv_dir = os.path.split(os.path.split(python_exe)[0])[0]
            venv_name = os.path.split(venv_dir)[1]
            python_dirs.update({venv_name: venv_dir})
        
        return python_dirs
    
    def venv_kernel_specs(self):
        python_dirs = self.find_kernel_paths()
        kspecs = {}
        for venv_name, venv_dir in python_dirs.items():
            exe_name = os.path.join(venv_dir, 'bin/python')
            kspec_dict =  {"argv": [exe_name,
                                    "-m",
                                    "IPython.kernel",
                                    "-f",
                                    "{connection_file}"],
                           "display_name": "conda ({})".format(venv_name),
                           "env": {}}

            kspecs.update({venv_name: KernelSpec(**kspec_dict)})
        return kspecs
    
    def find_kernel_specs(self):
        """Returns a dict mapping kernel names to resource directories."""
        d = super(CondaEnvKernelSpecManager, self).find_kernel_specs()
        
        d.update(self.find_kernel_paths())
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



if __name__ == '__main__':
    vspec = CondaEnvKernelSpecManager()
    print(vspec.venv_kernel_specs())
