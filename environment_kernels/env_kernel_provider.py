"""
Prototype implementation of a kernel provider interface developed in
https://github.com/jupyter/jupyter_client/pull/308

ToDo:
* refactor the backed logic (get_virtualenv_env_data and friends) to return something which bot sides can use
* Cleanup the options?
"""
import os

from jupyter_client.discovery import KernelProviderBase
from jupyter_client.manager2 import KernelManager2
from traitlets import List, Unicode, Int, Bool
from traitlets.config import LoggingConfigurable

from .utils import HAVE_CONDA


class BaseEnvironmentKernelProvider(KernelProviderBase, LoggingConfigurable):
    id = "INVALID_BaseEnvironmentKernelProvider"

    blacklist_envs = List(
        default_value=["conda__build"],
        config=True,
        help="Environments which should not be used even if a valid kernel exists in it.")

    whitelist_envs = List(
        default_value=[],
        config=True,
        help="Environments which should be used, all others are ignored (overwrites blacklist_envs).")

    display_name_template = Unicode(
        u"Environment ({})",
        config=True,
        help="Template for the kernel name in the UI. Needs to include '{}' for the name.")

    refresh_interval = Int(
        3,
        config=True,
        help="Interval (in minutes) to refresh the list of environment kernels. Setting it to '0' disables the refresh.")

    def __init__(self, **kwargs):
        super(BaseEnvironmentKernelProvider, self).__init__(**kwargs)
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
                self.log.info("Started periodic updates of the %s environment list (every %s minutes).", self.id,
                              self.refresh_interval)
            except:
                self.log.exception(
                    "Error while trying to enable periodic updates of the %s environment list." % self.id, )
        else:
            self.log.info("Periodical updates the %s environment list are DISABLED.", self.id)

    def discover_environment_kernels(self):
        raise NotImplementedError()

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
            self.log.info("Starting initial scan of %s environments...", self.id)
        else:
            self.log.debug("Starting periodic scan of %s environments...", self.id)
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
        env_data.update(self.discover_environment_kernels())

        env_data = {name: env_data[name] for name in env_data if self.validate_env(name)}
        new_kernels = [env for env in list(env_data.keys()) if env not in list(self._env_data_cache.keys())]
        if new_kernels:
            self.log.info("Found new kernels in environments: %s", ", ".join(new_kernels))

        self._env_data_cache = env_data
        return env_data

    def find_kernels(self):
        names_seen = set()
        kernels = self._get_env_data()
        for name, (resource_dir, kernel_spec), in kernels.items():
            # Files earlier in the search path shadow kernels from later ones
            if name in names_seen:
                continue
            names_seen.add(name)

            yield name, {
                # TODO: get full language info
                'language': {'name': kernel_spec.language},
                'display_name': kernel_spec.display_name,
                'argv': kernel_spec.argv,
            }

    def launch(self, name, cwd=None):
        ressource_dir, kernel_spec = self._get_env_data()[name]

        # the call to the kernel_spec.env will run activate, so is quite costly...
        return KernelManager2(kernel_cmd=kernel_spec.argv, extra_env=kernel_spec.env,
                              cwd=cwd)


class CondaEnvironmentKernelProvider(BaseEnvironmentKernelProvider):
    id = 'conda'

    # Take the default home DIR for conda as the default
    _default_conda_dirs = ['~/.conda/envs/']

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
        default_value=_default_conda_dirs,
        config=True,
        help="List of directories in which are conda environments.")

    conda_prefix_template = Unicode(
        u"conda_{}",
        config=True,
        help="Template for the conda environment kernel name prefix in the UI. Needs to include {} for the name.")

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
        help="Probe for conda environments by calling conda itself.")

    def discover_environment_kernels(self):
        from .envs_conda import get_conda_env_data
        return get_conda_env_data(self)


class VirtualenvEnvironmentKernelProvider(BaseEnvironmentKernelProvider):
    id = 'virtualenv'

    find_virtualenv_envs = Bool(True,
                                config=True,
                                help="Probe for virtualenv environments.")

    # Take the default home DIR for virtualenv as the default
    _default_virtualenv_dirs = ['~/.virtualenvs']

    virtualenv_env_dirs = List(
        default_value=_default_virtualenv_dirs,
        config=True,
        help="List of directories in which are virtualenv environments.")

    virtualenv_prefix_template = Unicode(
        u"virtualenv_{}",
        config=True,
        help="Template for the virtualenv environment kernel name prefix in the UI. Needs to include {} for the name.")

    def discover_environment_kernels(self):
        from .envs_virtualenv import get_virtualenv_env_data
        return get_virtualenv_env_data(self)
