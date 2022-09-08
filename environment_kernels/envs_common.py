# coding: utf-8
"""Common function to deal with virtual environments"""
from __future__ import absolute_import

import platform
import os
import glob

from .env_kernelspec import EnvironmentLoadingKernelSpec

JLAB_MINVERSION_3 = None

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
            mgr.log.debug(
                "Found duplicate env kernel: %s, which would again point to %s. Using the first!",
                kernel_name, venv_dir)
            continue
        argv, language, resource_dir, metadata = validator_func(venv_dir)
        if not argv:
            # probably does not contain the kernel type (e.g. not R or python or does not contain
            # the kernel code itself)
            continue
        display_name = display_name_template.format(kernel_name)
        kspec_dict = {"argv": argv, "language": language,
                      "display_name": display_name,
                      "resource_dir": resource_dir,
                      "metadata": metadata
                      }

        # the default vars are needed to save the vars in the function context
        def loader(env_dir=venv_dir, activate_func=activate_func, mgr=mgr):
            mgr.log.debug("Loading env data for %s" % env_dir)
            res = activate_func(mgr, env_dir)
            # mgr.log.info("PATH: %s" % res['PATH'])
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
        return [], None, None, {}

    # Make some checks for ipython first, because calling the import is expensive
    if find_exe(venv_dir, "ipython") is None:
        if find_exe(venv_dir, "ipython2") is None:
            if find_exe(venv_dir, "ipython3") is None:
                return [], None, None, {}

    # check if this is really an ipython **kernel**
    import subprocess
    try:
        subprocess.check_call([python_exe_name, '-c', 'import ipykernel'], stderr=subprocess.DEVNULL)
    except:
        # not installed? -> not useable in any case...
        return [], None, None, {}

    argv = [python_exe_name, "-m", "ipykernel", "-f", "{connection_file}"]
    resources_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logos", "python")

    metadata = {}
    if is_jlab_minversion_3() and is_ipykernel_minversion_6(python_exe_name):
        #print(f"{python_exe_name} supports debugger")
        metadata["debugger"] = True
    return argv, "python", resources_dir, metadata


def validate_IRkernel(venv_dir):
    """Validates that this env contains an IRkernel kernel and returns info to start it


    Returns: tuple
        (ARGV, language, resource_dir, metadata)
    """
    r_exe_name = find_exe(venv_dir, "R")
    if r_exe_name is None:
        return [], None, None, None

    # check if this is really an IRkernel **kernel**
    import subprocess
    ressources_dir = None
    try:
        print_resources = 'cat(as.character(system.file("kernelspec", package = "IRkernel")))'
        resources_dir_bytes = subprocess.check_output([r_exe_name, '--slave', '-e', print_resources])
        resources_dir = resources_dir_bytes.decode(errors='ignore')
    except:
        # not installed? -> not useable in any case...
        return [], None, None, None
    argv = [r_exe_name, "--slave", "-e", "IRkernel::main()", "--args", "{connection_file}"]
    if not os.path.exists(resources_dir.strip()):
        # Fallback to our own log, but don't get the nice js goodies...
        resources_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logos", "r")
    return argv, "r", resources_dir, dict()


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


def is_ipykernel_minversion_6(python_exe_name):
    import subprocess
    try:
        subprocess.check_call([python_exe_name, '-c', '''
import sys
import ipykernel
if int(ipykernel.__version__.split('.', maxsplit=1)[0]) >= 6:
    sys.exit(0)
sys.exit(-1)
'''
        ], stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        return False


def is_jlab_minversion_3():
    global JLAB_MINVERSION_3
    if JLAB_MINVERSION_3 is not None:
        return JLAB_MINVERSION_3

    try:
        import jupyterlab
        JLAB_MINVERSION_3 = int(jupyterlab.__version__.split('.', maxsplit=1)[0]) >= 3
    except ModuleNotFoundError:
        JLAB_MINVERSION_3 = False
    return JLAB_MINVERSION_3
