# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
import os.path

from jupyter_client.kernelspec import (KernelSpecManager, NoSuchKernel)
from traitlets import List, Unicode, Bool, Int

from .envs_conda import get_conda_env_data
from .envs_virtualenv import get_virtualenv_env_data
from .utils import FileNotFoundError, HAVE_CONDA

ENV_SUPPLYER = [get_conda_env_data, get_virtualenv_env_data]

__all__ = ['EnvironmentKernelSpecManager']


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
        import conda
        _default_conda_dirs += conda.config.envs_dirs

    # Remove any duplicates
    _default_conda_dirs = list(set(map(os.path.expanduser,
                                       _default_conda_dirs)))

    conda_env_dirs = List(
        _default_conda_dirs,
        config=True,
        help="List of directories in which are conda environments.")

    virtualenv_env_dirs = List(
        _default_virtualenv_dirs,
        config=True,
        help="List of directories in which are virtualenv environments.")

    blacklist_envs = List(
        ["conda__build"],
        config=True,
        help="Environments which should not be used even if a ipykernel exists in it.")

    whitelist_envs = List(
        [],
        config=True,
        help="Environments which should be used, all others are ignored (overwrites blacklist_envs).")

    display_name_template = Unicode(
        u"Environment ({})",
        config=True,
        help="Template for the kernel name in the UI. Needs to include {} for the name.")

    conda_prefix_template = Unicode(
        u"conda_{}",
        config=True,
        help="Template for the conda environment kernel name prefix in the UI. Needs to include {} for the name.")

    virtualenv_prefix_template = Unicode(
        u"virtualenv_{}",
        config=True,
        help="Template for the virtualenv environment kernel name prefix in the UI. Needs to include {} for the name.")

    find_conda_envs = Bool(
        True,
        config=True,
        help="Probe for conda environments, including calling conda itself.")

    find_r_envs = Bool(
        True,
        config=True,
        help="Probe environments for R kernels (currently only conda environments).")

    use_conda_directly = Bool(
        True,
        config=True,
        help="Probe for conda environments by calling conda itself. Only relevant if find_conda_envs is True.")

    refresh_interval = Int(
        3,
        config=True,
        help="Interval (in minutes) to refresh the list of environment kernels. Setting it to '0' disables the refresh.")

    find_virtualenv_envs = Bool(True,
                                config=True,
                                help="Probe for virtualenv environments.")

    def __init__(self, *args, **kwargs):
        super(EnvironmentKernelSpecManager, self).__init__(*args, **kwargs)
        self.log.info("Using EnvironmentKernelSpecManager...")
        self._env_data_cache = {}
        if self.refresh_interval > 0:
            try:
                from tornado.ioloop import PeriodicCallback, IOLoop
                # Initial loading NOW
                IOLoop.current().call_later(0, callback=self._update_env_data, initial=True)
                # Later updates
                updater = PeriodicCallback(callback=self._update_env_data,
                                           callback_time=1000 * 60 * self.refresh_interval)
                updater.start()
                if not updater.is_running():
                    raise Exception()
                self._periodic_updater = updater
                self.log.info("Started periodic updates of the kernel list (every %s minutes).", self.refresh_interval)
            except:
                self.log.exception("Error while trying to enable periodic updates of the kernel list.")
        else:
            self.log.info("Periodical updates the kernel list are DISABLED.")

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

    def _update_env_data(self, initial=False):
        if initial:
            self.log.info("Starting initial scan of virtual environments...")
        else:
            self.log.debug("Starting periodic scan of virtual environments...")
        self._get_env_data(reload=True)
        self.log.debug("done.")

    def _get_env_data(self, reload=False):
        """Get the data about the available environments.

        env_data is a structure {name -> (resourcedir, kernel spec)}
        """

        # This is called much too often and finding-process is really expensive :-(
        if not reload and getattr(self, "_env_data_cache", {}):
            return getattr(self, "_env_data_cache")

        env_data = {}
        for supplyer in ENV_SUPPLYER:
            env_data.update(supplyer(self))

        env_data = {name: env_data[name] for name in env_data if self.validate_env(name)}
        new_kernels = env_data.keys() - self._env_data_cache.keys()
        if new_kernels:
            self.log.info("Found new kernels in environments: %s", ", ".join(new_kernels))

        self._env_data_cache = env_data
        return env_data

    def find_kernel_specs_for_envs(self):
        """Returns a dict mapping kernel names to resource directories."""
        data = self._get_env_data()
        return {name: data[name][0] for name in data}

    def get_all_kernel_specs_for_envs(self):
        """Returns the dict of name -> kernel_spec for all environments"""

        data = self._get_env_data()
        return {name: data[name][1] for name in data}

    def find_kernel_specs(self):
        """Returns a dict mapping kernel names to resource directories."""
        # let real installed kernels overwrite envs with the same name:
        # this is the same order as the get_kernel_spec way, which also prefers
        # kernels from the jupyter dir over env kernels.
        specs = self.find_kernel_specs_for_envs()
        specs.update(super(EnvironmentKernelSpecManager,
                           self).find_kernel_specs())
        return specs

    def get_all_specs(self):
        """Returns a dict mapping kernel names and resource directories.
        """
        # This is new in 4.1 -> https://github.com/jupyter/jupyter_client/pull/93
        specs = self.get_all_kernel_specs_for_envs()
        specs.update(super(EnvironmentKernelSpecManager, self).get_all_specs())
        return specs

    def get_kernel_spec(self, kernel_name):
        """Returns a :class:`KernelSpec` instance for the given kernel_name.

        Raises :exc:`NoSuchKernel` if the given kernel name is not found.
        """
        try:
            return super(EnvironmentKernelSpecManager,
                         self).get_kernel_spec(kernel_name)
        except (NoSuchKernel, FileNotFoundError):
            venv_kernel_name = kernel_name.lower()
            specs = self.get_all_kernel_specs_for_envs()
            if venv_kernel_name in specs:
                return specs[venv_kernel_name]
            else:
                raise NoSuchKernel(kernel_name)
