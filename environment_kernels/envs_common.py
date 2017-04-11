# coding: utf-8
"""Common function to deal with virtual environments"""
from __future__ import absolute_import

import platform
import os
import glob

from .env_kernelspec import EnvironmentLoadingKernelSpec


def find_env_paths_in_basedirs(base_dirs):
    """Returns all potential envs in a basedir"""
    # get potential env path in the base_dirs
    env_path = []
    for base_dir in base_dirs:
        env_path.extend(glob.glob(os.path.join(
            os.path.expanduser(base_dir), '*', '')))
    # self.log.info("Found the following kernels from config: %s", ", ".join(venvs))

    return env_path


def convert_to_env_data(mgr, env_paths, validator_func, activate_func,
                        name_template, display_name_template, name_prefix):
    """Converts a list of paths to environments to env_data.

    env_data is a structure {name -> (ressourcedir, kernel spec)}
    """
    env_data = {}
    for venv_dir in env_paths:
        venv_name = os.path.split(os.path.abspath(venv_dir))[1]
        kernel_name = name_template.format(name_prefix + venv_name)
        kernel_name = kernel_name.lower()
        if kernel_name in env_data:
            mgr.log.error(
                "Duplicate env kernels: %s would both point to %s and %s. Using the first!",
                kernel_name, env_data[kernel_name], venv_dir)
            continue
        argv, language, resource_dir = validator_func(venv_dir)
        if not argv:
            # probably does not contain the kernel type (e.g. not R or python or does not contain
            # the kernel code itself)
            continue
        display_name = display_name_template.format(kernel_name)
        kspec_dict = {"argv": argv, "language": language,
                      "display_name": display_name,
                      "resource_dir": resource_dir
                      }

        # the default vars are needed to save the vars in the function context
        def loader(env_dir=venv_dir, activate_func=activate_func, mgr=mgr):
            mgr.log.debug("Loading env data for %s" % env_dir)
            res = activate_func(mgr, env_dir)
            #mgr.log.info("PATH: %s" % res['PATH'])
            return res

        kspec = EnvironmentLoadingKernelSpec(loader, **kspec_dict)
        env_data.update({kernel_name: (resource_dir, kspec)})
    return env_data


def validate_IPykernel(venv_dir):
    """Validates that this env contains an IPython kernel and returns info to start it


    Returns: tuple
        (ARGV, language, resource_dir)
    """
    python_exe_name = find_exe(venv_dir, "python")
    if python_exe_name is None:
        python_exe_name = find_exe(venv_dir, "python2")
    if python_exe_name is None:
        python_exe_name = find_exe(venv_dir, "python3")
    if python_exe_name is None:
        return [], None, None

    # Make some checks for ipython first, because calling the import is expensive
    if find_exe(venv_dir, "ipython") is None:
        if find_exe(venv_dir, "ipython2") is None:
            if find_exe(venv_dir, "ipython3") is None:
                return [], None, None

    # check if this is really an ipython **kernel**
    import subprocess
    try:
        subprocess.check_call([python_exe_name, '-c', '"import ipykernel"'])
    except:
        # not installed? -> not useable in any case...
        return [], None, None
    argv = [python_exe_name, "-m", "ipykernel", "-f", "{connection_file}"]
    resources_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logos", "python")
    return argv, "python", resources_dir


def validate_IRkernel(venv_dir):
    """Validates that this env contains an IRkernel kernel and returns info to start it


    Returns: tuple
        (ARGV, language, resource_dir)
    """
    r_exe_name = find_exe(venv_dir, "r")
    if r_exe_name is None:
        return [], None, None

    # check if this is really an ipython **kernel**
    import subprocess
    try:
        subprocess.check_call([r_exe_name, '--slave', '-e', 'library(IRkernel)'])
    except:
        # not installed? -> not useable in any case...
        return [], None, None
    argv = [r_exe_name, "--slave", "-e", "IRkernel::main()", "--args", "{connection_file}"]
    resources_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logos", "r")
    return argv, "r", resources_dir


def find_exe(env_dir, name):
    """Finds a exe with that name in the environment path"""

    if platform.system() == "Windows":
        name = name + ".exe"

    # find the binary
    exe_name = os.path.join(env_dir, name)
    if not os.path.exists(exe_name):
        exe_name = os.path.join(env_dir, "bin", name)
        if not os.path.exists(exe_name):
            exe_name = os.path.join(env_dir, "Scripts", name)
            if not os.path.exists(exe_name):
                return None
    return exe_name
