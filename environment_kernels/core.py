# -*- coding: utf-8 -*-

import os
import glob
import platform

from jupyter_client.kernelspec import KernelSpecManager, KernelSpec, NoSuchKernel
from traitlets import List

__all__ = ['EnvironmentKernelSpecManager']

try:
    import conda.config
    HAVE_CONDA = True

except ImportError:
    HAVE_CONDA = False


class EnvironmentKernelSpecManager(KernelSpecManager):
    """
    A Jupyter Kenel manager which dyamically checks for Environments

    Given a list of base directories, this class searches for the pattern::

        BASE_DIR/NAME/bin/ipython

    where NAME is taken to be the name of the environment.
    """

    # Take the default home DIR for conda and virtualenv as the default
    _default_dirs = ['~/.conda/envs/', '~/.virtualenvs']

    # Check for the CONDA_ENV_PATH variable and add it to the list if set.
    if os.environ.get('CONDA_ENV_PATH', False):
        _default_dirs.append(os.environ['CONDA_ENV_PATH'].split('envs')[0])

    # If we are running inside the root conda env can get all the env dirs:
    if HAVE_CONDA:
        _default_dirs += conda.config.envs_dirs

    # Remove any duplicates
    _default_dirs = list(set(map(os.path.expanduser, _default_dirs)))

    env_dirs = List(_default_dirs, config=True)
    extra_env_dirs = List([], config=True)
    blacklist_envs = List([], config=True)
    whitelist_envs = List([], config=True)

    def validate_env(self, envname):
        """
        Check the name of the environment against the black list and the
        whitelist. If a whitelist is specified only it is checked.
        """
        if self.whitelist_envs and envname in self.whitelist_envs:
            return True
        elif self.whitelist_envs:
            return False

        if self.blacklist_envs and envname not in self.blacklist_envs:
            return True
        elif self.blacklist_envs:
            return False
        else:
            return True

    def _get_env_paths(self):
        if platform.system() == 'Windows':
            search = '*/Scripts/ipython'
        else:
            search = '*/bin/ipython'

        return [os.path.join(os.path.expanduser(base_dir), search)
                for base_dir in self.env_dirs + self.extra_env_dirs]

    def find_python_paths(self):
        # find a python executeable
        python_dirs = {}

        for env_path in self._get_env_paths():
            for python_exe in glob.glob(env_path):
                venv_dir = os.path.split(os.path.split(python_exe)[0])[0]
                venv_name = os.path.split(venv_dir)[1]
                if self.validate_env(venv_name):
                    python_dirs.update({venv_name: venv_dir})

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

            kspecs.update({"env_{}".format(venv_name): KernelSpec(**kspec_dict)})
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
        try:
            return super(EnvironmentKernelSpecManager, self).get_kernel_spec(kernel_name)
        except (NoSuchKernel, FileNotFoundError):
            venv_kernel_name = "env_{}".format(kernel_name.lower())
            if venv_kernel_name in self.venv_kernel_specs():
                return self.venv_kernel_specs()[venv_kernel_name]
            else:
                raise NoSuchKernel(kernel_name)
