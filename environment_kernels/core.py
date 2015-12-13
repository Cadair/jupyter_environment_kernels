# -*- coding: utf-8 -*-

import os
import os.path
from os.path import join as pj
import glob
import platform

from jupyter_client.kernelspec import KernelSpecManager, KernelSpec, NoSuchKernel
from ipykernel.kernelspec import RESOURCES

from traitlets import List, Unicode

__all__ = ['EnvironmentKernelSpecManager']

try:
    import conda.config
    HAVE_CONDA = True

except ImportError:
    HAVE_CONDA = False

try:
    FileNotFoundError
except NameError:
    #py2
    FileNotFoundError = IOError

class EnvironmentKernelSpecManager(KernelSpecManager):
    """
    A Jupyter Kernel manager which dyamically checks for Environments

    Given a list of base directories, this class searches for the pattern::

        BASE_DIR/NAME/{bin|Skript}/ipython

    where NAME is taken to be the name of the environment.
    """

    # Take the default home DIR for conda and virtualenv as the default
    _default_conda_dirs = ['~/.conda/envs/']
    _default_virtualenv_dirs = ['~/.virtualenvs']

    # Check for the CONDA_ENV_PATH variable and add it to the list if set.
    if os.environ.get('CONDA_ENV_PATH', False):
        _default_conda_dirs.append(os.environ['CONDA_ENV_PATH'].split('envs')[0])

    # If we are running inside the root conda env can get all the env dirs:
    if HAVE_CONDA:
        _default_conda_dirs += conda.config.envs_dirs

    # Remove any duplicates
    _default_conda_dirs = list(set(map(os.path.expanduser, _default_conda_dirs)))

    conda_env_dirs = List(
        _default_conda_dirs, config=True,
        help="List of directories in which are conda environments."
    )

    virtualenv_env_dirs = List(
        _default_virtualenv_dirs, config=True,
        help="List of directories in which are virtualenv environments."
    )

    blacklist_envs = List(
        ["conda__build"], config=True,
        help="Environments which should not be used even if a ipykernel exists in it."
    )

    whitelist_envs = List(
        [], config=True,
        help="Environments which should be used (overwrites a blacklist)."
    )

    display_name_template = Unicode(
        u"Environment ({})", config=True,
        help="Template for the kernel name in the UI. Needs to include {} for the name."
    )

    def __init__(self, *args, **kwargs):
        super(EnvironmentKernelSpecManager, self).__init__(*args, **kwargs)
        self.log.info("Using EnvironmentKernelSpecManager...")


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
            # If there is just a True, all envs are blacklisted
            return False
        else:
            return True

    def _find_conda_env_paths_from_conda(self):
        """Returns a list of path as given by `conda env list --json`.

        Returns empty list, if conda couldn't be called.
        """
        # use the cache, because using conda all the time is slow...
        import subprocess
        import json
        try:
            p = subprocess.Popen(
                ['conda', 'env', 'list', '--json'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE)
            comm = p.communicate()
            output = comm[0].decode()
            if p.returncode != 0 or len(output) == 0:
                self.log.error("Couldn't call 'conda' to get the environments. "
                               "Output:\n%s" , str(comm))
                return []
        except FileNotFoundError:
            self.log.error("'conda' not found in path.")
            return []
        output = json.loads(output)
        envs = output["envs"]
        #self.log.info("Found the following kernels from conda: %s", ", ".join(envs))
        return envs


    def _find_conda_env_path_from_config(self):
        """Returns a list of env paths as by using the configured conda env basedir"""
        return self._find_env_paths_in_basedirs(self.conda_env_dirs)


    def _find_virtualenv_env_path_from_config(self):
        """Returns a list of env paths as by using the configured virtualenv basedir"""
        return self._find_env_paths_in_basedirs(self.virtualenv_env_dirs)


    def _validate_ipython_path(self, env_path):
        """Returns whether a ipython executable is in that env"""
        # We validate a dir if it has a ipython executable in one of the dirs
        # which ends up in PATH. The proper way would probably use the ipykernel
        # as ipython itself is no garantee that the env can also be used as a kernel
        # but it is close...
        ipython = "ipython.exe" if platform.system() == "Windows" else "ipython"
        for search_path in ['bin', 'Scripts']:
            ipython_path = pj(env_path, search_path, ipython)
            if os.path.exists(ipython_path):
                return True
        return False


    def _find_env_paths_in_basedirs(self, base_dirs):
        """Returns all potential envs in a basedir"""
        # get potential env path in the base_dirs
        envs = []
        for base_dir in base_dirs:
            envs.extend(glob.glob(pj(os.path.expanduser(base_dir), '*', '')))
        #self.log.info("Found the following kernels from config: %s", ", ".join(venvs))

        # filter out envs which do not contain a ipython (~= ipkernel)
        envs = [env for env in envs if self._validate_ipython_path(env)]

        return envs


    def _convert_to_envs(self, env_paths, nametemplate):
        """Returns a dict of kernel_name -> path

        kernelname is build by using the template.
        """
        envs = {}
        for venv_dir in env_paths:
            venv_name = os.path.split(venv_dir)[1]
            kernel_name = nametemplate.format(venv_name)
            kernel_name = kernel_name.lower()
            if kernel_name in envs:
                self.log.error("Duplicate env kernels: %s would both point to %s and %s. Using the first!", kernel_name, envs[kernel_name], venv_dir)
                continue
            if self.validate_env(kernel_name):
                envs.update({kernel_name: venv_dir})
            else:
                self.log.info("Not considered env kernel (blacklisted): %s", kernel_name)
        return envs


    def _find_conda_envs(self):
        """Returns conda envs as dict of name -> path"""
        paths = self._find_conda_env_path_from_config()
        paths.extend(self._find_conda_env_paths_from_conda())
        paths = list(set(paths))

        # can't use '/' as that results in javascript errors :-/
        # need to use something which matches \w to get logos:
        # https://github.com/jupyter/notebook/issues/853
        templ = "conda_{}"
        return self._convert_to_envs(paths, templ)


    def _find_virtualenv_envs(self):
        """Returns virtualenv envs as dict of name -> path"""
        paths = self._find_virtualenv_env_path_from_config()

        templ = "virtualenv_{}"
        return self._convert_to_envs(paths, templ)


    def find_envs(self):
        """Returns for all envs as dict of name -> path"""

        # This is called much too often and the conda calls are really expensive :-(
        if hasattr(self, "_find_envs_cache"):
            return getattr(self, "_find_envs_cache")

        envs = {}
        envs.update(self._find_conda_envs())
        envs.update(self._find_virtualenv_envs())
        if envs:
            self.log.info("Found the following kernels for environments: %s", ", ".join(list(envs)))
        else:
            self.log.info("Found no kernels from environments!")
        self._find_envs_cache = envs
        return envs


    def _build_kernel_specs(self):
        """Returns the dict of name -> kernel_spec for all environments"""

        # This is called much too often and the conda calls are really expensive :-(
        if hasattr(self, "_build_kernel_specs_cache"):
            return getattr(self, "_build_kernel_specs_cache")

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
                           "language": "python",
                           "display_name": self.display_name_template.format(venv_name),
                           "env": {}}
            # This should probably use self.kernel_spec_class instead of the direct class
            kspecs.update({venv_name: KernelSpec(resource_dir=RESOURCES, **kspec_dict)})
        self._build_kernel_specs_cache = kspecs
        return kspecs

    def find_kernel_specs_for_envs(self):
        """Returns a dict mapping kernel names to resource directories."""
        # as the envs do not have logos (=resources) included, add in the
        # normal ones for python

        envs = self.find_envs()
        ret = {}
        for name in envs:
            ret[name] = RESOURCES
        return ret


    def find_kernel_specs(self):
        """Returns a dict mapping kernel names to resource directories."""
        # let real installed kernels overwrite envs with the same name:
        # this is the same order as the get_kernel_spec way, which also prefers
        # kernels from the jupyter dir over env kernels.
        specs = self.find_kernel_specs_for_envs()
        specs.update(super(EnvironmentKernelSpecManager, self).find_kernel_specs())
        return specs


    def get_kernel_spec(self, kernel_name):
        """Returns a :class:`KernelSpec` instance for the given kernel_name.

        Raises :exc:`NoSuchKernel` if the given kernel name is not found.
        """
        try:
            return super(EnvironmentKernelSpecManager, self).get_kernel_spec(kernel_name)
        except (NoSuchKernel, FileNotFoundError):
            venv_kernel_name = kernel_name.lower()
            specs = self._build_kernel_specs()
            if venv_kernel_name in specs:
                return specs[venv_kernel_name]
            else:
                raise NoSuchKernel(kernel_name)
