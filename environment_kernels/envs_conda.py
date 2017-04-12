# -*- coding: utf-8 -*-
"""Functions related to finding conda environments (both Python and R based)"""
from __future__ import absolute_import

from .activate_helper import source_env_vars_from_command
from .envs_common import (find_env_paths_in_basedirs, convert_to_env_data,
                          validate_IPykernel, validate_IRkernel)
from .utils import FileNotFoundError, ON_WINDOWS

def get_conda_env_data(mgr):
    """Finds kernel specs from conda environments

    env_data is a structure {name -> (resourcedir, kernel spec)}
    """
    if not mgr.find_conda_envs:
        return {}

    mgr.log.debug("Looking for conda environments in %s...", mgr.conda_env_dirs)

    # find all potential env paths
    env_paths = find_env_paths_in_basedirs(mgr.conda_env_dirs)
    env_paths.extend(_find_conda_env_paths_from_conda(mgr))
    env_paths = list(set(env_paths)) # remove duplicates

    mgr.log.debug("Scanning conda environments for python kernels...")
    env_data = convert_to_env_data(mgr=mgr,
                                   env_paths=env_paths,
                                   validator_func=validate_IPykernel,
                                   activate_func=_get_env_vars_for_conda_env,
                                   name_template=mgr.conda_prefix_template,
                                   display_name_template=mgr.display_name_template,
                                   name_prefix="")  # lets keep the py kernels without a prefix...
    if mgr.find_r_envs:
        mgr.log.debug("Scanning conda environments for R kernels...")
        env_data.update(convert_to_env_data(mgr=mgr,
                                            env_paths=env_paths,
                                            validator_func=validate_IRkernel,
                                            activate_func=_get_env_vars_for_conda_env,
                                            name_template=mgr.conda_prefix_template,
                                            display_name_template=mgr.display_name_template,
                                            name_prefix="r_"))
    return env_data


def _get_env_vars_for_conda_env(mgr, env_path):
    if ON_WINDOWS:
        args = ['activate', env_path]
    else:
        args = ['source', 'activate', env_path]

    try:
        envs = source_env_vars_from_command(args)
        #mgr.log.debug("PATH: %s", envs['PATH'])
        return envs
    except:
        # as a fallback, don't activate...
        mgr.log.exception(
            "Couldn't get environment variables for commands: %s", args)
        return {}


def _find_conda_env_paths_from_conda(mgr):
    """Returns a list of path as given by `conda env list --json`.

    Returns empty list, if conda couldn't be called.
    """
    # this is expensive, so make it configureable...
    if not mgr.use_conda_directly:
        return []
    mgr.log.debug("Looking for conda environments by calling conda directly...")
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
            mgr.log.error(
                "Couldn't call 'conda' to get the environments. "
                "Output:\n%s", str(comm))
            return []
    except FileNotFoundError:
        mgr.log.error("'conda' not found in path.")
        return []
    output = json.loads(output)
    envs = output["envs"]
    # self.log.info("Found the following kernels from conda: %s", ", ".join(envs))
    return envs
