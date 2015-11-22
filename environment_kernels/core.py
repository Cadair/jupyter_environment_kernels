# -*- coding: utf-8 -*-

import os
import os.path
from os.path import join as pj
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
    A Jupyter Kernel manager which dyamically checks for Environments

    Given a list of base directories, this class searches for the pattern::

        BASE_DIR/NAME/{bin|Skript}/ipython

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
    blacklist_envs = List(["_build"], config=True)
    whitelist_envs = List([], config=True)

    search_paths = List(['bin', 'Scripts'], config=True)

    _conda_env_output_cache = None
    _find_venvs_cache = None

    def __init__(self, *args, **kwargs):
        super(EnvironmentKernelSpecManager, self).__init__(*args, **kwargs)
        self.log.info("Using EnvironmentKernelSpecManager...")
        self.all_venv_kernel_specs = self.venv_kernel_specs()


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

    def _get_env_paths_from_conda(self):
        """Returns a list of path as given by `conda env list --json`.

        Raises :exc:`RuntimeError` if conda couldn't be called.
        """
        # use the cache, because using conda all the time is slow...
        if self._conda_env_output_cache is not None:
            return self._conda_env_output_cache
        import subprocess
        import json
        p = subprocess.Popen(
            ['conda', 'env', 'list', '--json'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE)
        comm = p.communicate()
        output = comm[0].decode()
        if p.returncode != 0 or len(output) == 0:
            raise RuntimeError("Couldn't call conda to get the environments. "
                               "Output:\n%s" % str(comm))

        output = json.loads(output)
        envs = output["envs"]
        # cache the output, as it is slow...
        self._conda_env_output_cache = envs
        #self.log.info("Found the following kernels from conda: %s", ", ".join(envs))
        return envs

    def _get_env_paths_from_config(self):
        # get portential env path from the config value (and environment variables)
        envs = []
        for base_dir in self.env_dirs + self.extra_env_dirs:
            envs.extend(glob.glob(pj(os.path.expanduser(base_dir), '*', '')))
        #self.log.info("Found the following kernels from config: %s", ", ".join(venvs))

        return envs

    def find_envs(self):
        if self._find_venvs_cache is not None:
            return self._find_venvs_cache
        potential_env_dirs = self._get_env_paths_from_config()
        try:
            potential_env_dirs.extend(self._get_env_paths_from_conda())
        except RuntimeError as e:
            print(e)
            pass

        # make unique
        potential_env_dirs = list(set(potential_env_dirs))

        ipython = "ipython.exe" if platform.system() == "Windows" else "ipython"

        env_paths = []
        for search_path in self.search_paths:
            for env_dir in potential_env_dirs:
                ipython_path = pj(env_dir, search_path, ipython)
                if os.path.exists(ipython_path):
                    env_paths.append(env_dir)


        envs = {}
        for venv_dir in env_paths:
            venv_name = os.path.split(venv_dir)[1]
            if self.validate_env(venv_name):
                envs.update({venv_name: venv_dir})
        self.log.info("Found the following kernels for environments: %s", ", ".join(list(envs)))
        self._find_venvs_cache = envs
        return envs

    def venv_kernel_specs(self):
        venv_dirs = self.find_envs()
        kspecs = {}
        if platform.system() == "Windows":
            python_exe_name = "python.exe"
        else:
            python_exe_name = "python"

        for venv_name, venv_dir in venv_dirs.items():
            # conda on windows has python.exe directly in the env
            exe_name = pj(venv_dir, python_exe_name)
            if not os.path.exists(exe_name):
                exe_name = pj(venv_dir, "bin", python_exe_name)
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
        d.update(self.find_envs())
        return d

    def get_kernel_spec(self, kernel_name):
        """Returns a :class:`KernelSpec` instance for the given kernel_name.

        Raises :exc:`NoSuchKernel` if the given kernel name is not found.
        """
        try:
            return super(EnvironmentKernelSpecManager, self).get_kernel_spec(kernel_name)
        except (NoSuchKernel, FileNotFoundError):
            venv_kernel_name = "env_{}".format(kernel_name.lower())
            if venv_kernel_name in self.all_venv_kernel_specs:
                return self.all_venv_kernel_specs[venv_kernel_name]
            else:
                raise NoSuchKernel(kernel_name)
