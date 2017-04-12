# -*- coding: utf-8 -*-
"""Functions related to finding virtualenv environments (python only)"""
from __future__ import absolute_import

import os

from .utils import ON_WINDOWS
from .activate_helper import source_env_vars_from_command
from .envs_common import find_env_paths_in_basedirs, convert_to_env_data, validate_IPykernel


def get_virtualenv_env_data(mgr):
    """Finds kernel specs from virtualenv environments

    env_data is a structure {name -> (resourcedir, kernel spec)}
    """

    if not mgr.find_virtualenv_envs:
        return {}

    mgr.log.debug("Looking for virtualenv environments in %s...", mgr.virtualenv_env_dirs)

    # find all potential env paths
    env_paths = find_env_paths_in_basedirs(mgr.virtualenv_env_dirs)

    mgr.log.debug("Scanning virtualenv environments for python kernels...")
    env_data = convert_to_env_data(mgr=mgr,
                                   env_paths=env_paths,
                                   validator_func=validate_IPykernel,
                                   activate_func=_get_env_vars_for_virtualenv_env,
                                   name_template=mgr.conda_prefix_template,
                                   display_name_template=mgr.display_name_template,
                                   name_prefix="")  # virtualenv has only python, so no need for a
    # prefix
    return env_data


def _get_env_vars_for_virtualenv_env(mgr, env_path):
    if ON_WINDOWS:
        args = [os.path.join(env_path, "Shell", "activate")]
    else:
        args = ['source', os.path.join(env_path, "bin", "activate")]
    try:
        envs = source_env_vars_from_command(args)
        # mgr.log.debug("Environment variables: %s", envs)
        return envs
    except:
        # as a fallback, don't activate...
        mgr.log.exception(
            "Couldn't get environment variables for commands: %s", args)
        return {}
