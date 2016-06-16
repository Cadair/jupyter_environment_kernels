# -*- coding: utf-8 -*-
# Copyright 2015, the xonsh developers. All rights reserved.
"""Helpers to activate an environment and prepare the environment variables for the kernel.
Copied from xonsh"""

# Changes from xonsh:
# - replace the xonsh environment cache with os.environ
# - remove aliases and func handling -> we are only interested on environment variables
# - remove xonsh special ENV thingy and "detype()"
# - add source_bash and source_zsh
# - Changed the default for "save" in all function definitions/parser to False to get exceptions

import os
import platform
from argparse import ArgumentParser
import subprocess
from tempfile import NamedTemporaryFile
import re
import sys
from itertools import chain


ON_DARWIN = platform.system() == 'Darwin'
ON_LINUX = platform.system() == 'Linux'
ON_WINDOWS = platform.system() == 'Windows'

PYTHON_VERSION_INFO = sys.version_info[:3]
ON_ANACONDA = any(s in sys.version for s in {'Anaconda', 'Continuum'})


ON_POSIX = (os.name == 'posix')

def source_bash(args, stdin=None):
    """Simply bash-specific wrapper around source-foreign

    Returns a dict to be used as a new environment"""
    args = list(args)
    new_args = ['bash', '--sourcer=source']
    new_args.extend(args)
    return source_foreign(new_args, stdin=stdin)

def source_zsh(args, stdin=None):
    """Simply zsh-specific wrapper around source-foreign

    Returns a dict to be used as a new environment"""
    args = list(args)
    new_args = ['zsh', '--sourcer=source']
    new_args.extend(args)
    return source_foreign(new_args, stdin=stdin)


def source_cmd(args, stdin=None):
    """Simple cmd.exe-specific wrapper around source-foreign.

    returns a dict to be used as a new environment
    """
    args = list(args)
    fpath = locate_binary(args[0])
    args[0] = fpath if fpath else args[0]
    if not os.path.isfile(args[0]):
        raise RuntimeError("Command not found: %s" % args[0])
    prevcmd = 'call '
    prevcmd += ' '.join([argvquote(arg, force=True) for arg in args])
    prevcmd = escape_windows_cmd_string(prevcmd)
    args.append('--prevcmd={}'.format(prevcmd))
    args.insert(0, 'cmd')
    args.append('--interactive=0')
    args.append('--sourcer=call')
    args.append('--envcmd=set')
    args.append('--seterrpostcmd=if errorlevel 1 exit 1')
    args.append('--use-tmpfile=1')
    return source_foreign(args, stdin=stdin)


def locate_binary(name):
    if os.path.isfile(name) and name != os.path.basename(name):
        return name

    directories = os.environ.get('PATH').split(os.path.pathsep)

    # Windows users expect t obe able to execute files in the same directory without `./`
    if ON_WINDOWS:
        directories = [_get_cwd()] + directories

    try:
        return next(chain.from_iterable(yield_executables(directory, name) for directory in directories if os.path.isdir(directory)))
    except StopIteration:
        return None


def argvquote(arg, force=False):
    """ Returns an argument quoted in such a way that that CommandLineToArgvW
    on Windows will return the argument string unchanged.
    This is the same thing Popen does when supplied with an list of arguments.
    Arguments in a command line should be separated by spaces; this
    function does not add these spaces. This implementation follows the
    suggestions outlined here:
    https://blogs.msdn.microsoft.com/twistylittlepassagesallalike/2011/04/23/everyone-quotes-command-line-arguments-the-wrong-way/
    """
    if not force and len(arg) != 0 and not any([c in arg for c in ' \t\n\v"']):
        return arg
    else:
        n_backslashes = 0
        cmdline = '"'
        for c in arg:
            if c == '"':
                cmdline += (n_backslashes * 2 + 1) * '\\'
            else:
                cmdline += n_backslashes * '\\'
            if c != '\\':
                cmdline += c
                n_backslashes = 0
            else:
                n_backslashes += 1
        return cmdline + n_backslashes * 2 * '\\' + '"'


def escape_windows_cmd_string(s):
    """Returns a string that is usable by the Windows cmd.exe.
    The escaping is based on details here and emperical testing:
    http://www.robvanderwoude.com/escapechars.php
    """
    for c in '()%!^<>&|"':
        s = s.replace(c, '^' + c)
    s = s.replace('/?', '/.')
    return s


def source_foreign(args, stdin=None):
    """Sources a file written in a foreign shell language."""
    parser = _ensure_source_foreign_parser()
    ns = parser.parse_args(args)
    if ns.prevcmd is not None:
        pass  # don't change prevcmd if given explicitly
    elif os.path.isfile(ns.files_or_code[0]):
        # we have filename to source
        ns.prevcmd = '{} "{}"'.format(ns.sourcer, '" "'.join(ns.files_or_code))
    elif ns.prevcmd is None:
        ns.prevcmd = ' '.join(ns.files_or_code)  # code to run, no files
    fsenv = foreign_shell_data(shell=ns.shell, login=ns.login,
                                          interactive=ns.interactive,
                                          envcmd=ns.envcmd,
                                          aliascmd=ns.aliascmd,
                                          extra_args=ns.extra_args,
                                          safe=ns.safe, prevcmd=ns.prevcmd,
                                          postcmd=ns.postcmd,
                                          funcscmd=ns.funcscmd,
                                          sourcer=ns.sourcer,
                                          use_tmpfile=ns.use_tmpfile,
                                          seterrprevcmd=ns.seterrprevcmd,
                                          seterrpostcmd=ns.seterrpostcmd)
    if fsenv is None:
        raise RuntimeError("Source failed: {}\n".format(ns.prevcmd), 1)
    # apply results
    env = os.environ.copy()
    for k, v in fsenv.items():
        if k in env and v == env[k]:
            continue  # no change from original
        env[k] = v
    # Remove any env-vars that were unset by the script.
    for k in os.environ: # use os.environ again to prevent errors about changed size
        if k not in fsenv:
            env.pop(k, None)
    return env


def _get_cwd():
    try:
        return os.getcwd()
    except (OSError, FileNotFoundError):
        return None


def yield_executables_windows(directory, name):
    normalized_name = os.path.normcase(name)
    extensions = os.environ.get('PATHEXT')
    try:
        names = os.listdir(directory)
    except PermissionError:
        return
    for a_file in names:
        normalized_file_name = os.path.normcase(a_file)
        base_name, ext = os.path.splitext(normalized_file_name)

        if (
            normalized_name == base_name or normalized_name == normalized_file_name
        ) and ext.upper() in extensions:
            yield os.path.join(directory, a_file)


def yield_executables_posix(directory, name):
    try:
        names = os.listdir(directory)
    except PermissionError:
        return
    if name in names:
        path = os.path.join(directory, name)
        if _is_executable_file(path):
            yield path


yield_executables = yield_executables_windows if ON_WINDOWS else yield_executables_posix

def _is_executable_file(path):
    """Checks that path is an executable regular file, or a symlink towards one.
    This is roughly ``os.path isfile(path) and os.access(path, os.X_OK)``.

    This function was forked from pexpect originally:

    Copyright (c) 2013-2014, Pexpect development team
    Copyright (c) 2012, Noah Spurrier <noah@noah.org>

    PERMISSION TO USE, COPY, MODIFY, AND/OR DISTRIBUTE THIS SOFTWARE FOR ANY
    PURPOSE WITH OR WITHOUT FEE IS HEREBY GRANTED, PROVIDED THAT THE ABOVE
    COPYRIGHT NOTICE AND THIS PERMISSION NOTICE APPEAR IN ALL COPIES.
    THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
    WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
    MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
    ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
    WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
    ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
    OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
    """
    # follow symlinks,
    fpath = os.path.realpath(path)

    if not os.path.isfile(fpath):
        # non-files (directories, fifo, etc.)
        return False

    return os.access(fpath, os.X_OK)


_SOURCE_FOREIGN_PARSER = None


def _ensure_source_foreign_parser():
    global _SOURCE_FOREIGN_PARSER
    if _SOURCE_FOREIGN_PARSER is not None:
        return _SOURCE_FOREIGN_PARSER
    desc = "Sources a file written in a foreign shell language."
    parser = ArgumentParser('source-foreign', description=desc)
    parser.add_argument('shell', help='Name or path to the foreign shell')
    parser.add_argument('files_or_code', nargs='+',
                        help='file paths to source or code in the target '
                             'language.')
    parser.add_argument('-i', '--interactive', type=to_bool, default=True,
                        help='whether the sourced shell should be interactive',
                        dest='interactive')
    parser.add_argument('-l', '--login', type=to_bool, default=False,
                        help='whether the sourced shell should be login',
                        dest='login')
    parser.add_argument('--envcmd', default=None, dest='envcmd',
                        help='command to print environment')
    parser.add_argument('--aliascmd', default=None, dest='aliascmd',
                        help='command to print aliases')
    parser.add_argument('--extra-args', default=(), dest='extra_args',
                        type=(lambda s: tuple(s.split())),
                        help='extra arguments needed to run the shell')
    parser.add_argument('-s', '--safe', type=to_bool, default=False,
                        help='whether the source shell should be run safely, '
                             'and not raise any errors, even if they occur.',
                        dest='safe')
    parser.add_argument('-p', '--prevcmd', default=None, dest='prevcmd',
                        help='command(s) to run before any other commands, '
                             'replaces traditional source.')
    parser.add_argument('--postcmd', default='', dest='postcmd',
                        help='command(s) to run after all other commands')
    parser.add_argument('--funcscmd', default=None, dest='funcscmd',
                        help='code to find locations of all native functions '
                             'in the shell language.')
    parser.add_argument('--sourcer', default=None, dest='sourcer',
                        help='the source command in the target shell '
                        'language, default: source.')
    parser.add_argument('--use-tmpfile', type=to_bool, default=False,
                        help='whether the commands for source shell should be '
                             'written to a temporary file.',
                        dest='use_tmpfile')
    parser.add_argument('--seterrprevcmd', default=None, dest='seterrprevcmd',
                        help='command(s) to set exit-on-error before any'
                             'other commands.')
    parser.add_argument('--seterrpostcmd', default=None, dest='seterrpostcmd',
                        help='command(s) to set exit-on-error after all'
                             'other commands.')
    _SOURCE_FOREIGN_PARSER = parser
    return parser

def foreign_shell_data(shell, interactive=True, login=False, envcmd=None,
                       aliascmd=None, extra_args=(), currenv=None,
                       safe=False, prevcmd='', postcmd='', funcscmd=None,
                       sourcer=None, use_tmpfile=False, tmpfile_ext=None,
                       runcmd=None, seterrprevcmd=None, seterrpostcmd=None):
    """Extracts data from a foreign (non-xonsh) shells. Currently this gets
    the environment, aliases, and functions but may be extended in the future.

    Parameters
    ----------
    shell : str
        The name of the shell, such as 'bash' or '/bin/sh'.
    interactive : bool, optional
        Whether the shell should be run in interactive mode.
    login : bool, optional
        Whether the shell should be a login shell.
    envcmd : str or None, optional
        The command to generate environment output with.
    aliascmd : str or None, optional
        The command to generate alias output with.
    extra_args : tuple of str, optional
        Addtional command line options to pass into the shell.
    currenv : tuple of items or None, optional
        Manual override for the current environment.
    safe : bool, optional
        Flag for whether or not to safely handle exceptions and other errors.
    prevcmd : str, optional
        A command to run in the shell before anything else, useful for
        sourcing and other commands that may require environment recovery.
    postcmd : str, optional
        A command to run after everything else, useful for cleaning up any
        damage that the prevcmd may have caused.
    funcscmd : str or None, optional
        This is a command or script that can be used to determine the names
        and locations of any functions that are native to the foreign shell.
        This command should print *only* a JSON object that maps
        function names to the filenames where the functions are defined.
        If this is None, then a default script will attempted to be looked
        up based on the shell name. Callable wrappers for these functions
        will be returned in the aliases dictionary.
    sourcer : str or None, optional
        How to source a foreign shell file for purposes of calling functions
        in that shell. If this is None, a default value will attempt to be
        looked up based on the shell name.
    use_tmpfile : bool, optional
        This specifies if the commands are written to a tmp file or just
        parsed directly to the shell
    tmpfile_ext : str or None, optional
        If tmpfile is True this sets specifies the extension used.
    runcmd : str or None, optional
        Command line switches to use when running the script, such as
        -c for Bash and /C for cmd.exe.
    seterrprevcmd : str or None, optional
        Command that enables exit-on-error for the shell that is run at the
        start of the script. For example, this is "set -e" in Bash. To disable
        exit-on-error behavior, simply pass in an empty string.
    seterrpostcmd : str or None, optional
        Command that enables exit-on-error for the shell that is run at the end
        of the script. For example, this is "if errorlevel 1 exit 1" in
        cmd.exe. To disable exit-on-error behavior, simply pass in an
        empty string.

    Returns
    -------
    env : dict
        Dictionary of shell's environment
    aliases : dict
        Dictionary of shell's alaiases, this includes foreign function
        wrappers.
    """
    cmd = [shell]
    cmd.extend(extra_args)  # needs to come here for GNU long options
    if interactive:
        cmd.append('-i')
    if login:
        cmd.append('-l')
    shkey = CANON_SHELL_NAMES[shell]
    envcmd = DEFAULT_ENVCMDS.get(shkey, 'env') if envcmd is None else envcmd
    tmpfile_ext = DEFAULT_TMPFILE_EXT.get(shkey, 'sh') if tmpfile_ext is None else tmpfile_ext
    runcmd = DEFAULT_RUNCMD.get(shkey, '-c') if runcmd is None else runcmd
    seterrprevcmd = DEFAULT_SETERRPREVCMD.get(shkey, '') \
                        if seterrprevcmd is None else seterrprevcmd
    seterrpostcmd = DEFAULT_SETERRPOSTCMD.get(shkey, '') \
                        if seterrpostcmd is None else seterrpostcmd
    command = COMMAND.format(envcmd=envcmd, prevcmd=prevcmd,
                             postcmd=postcmd,
                             seterrprevcmd=seterrprevcmd,
                             seterrpostcmd=seterrpostcmd).strip()

    cmd.append(runcmd)

    if not use_tmpfile:
        cmd.append(command)
    else:
        tmpfile = NamedTemporaryFile(suffix=tmpfile_ext, delete=False)
        tmpfile.write(command.encode('utf8'))
        tmpfile.close()
        cmd.append(tmpfile.name)

    if currenv is not None:
        currenv = os.environ
    try:
        s = subprocess.check_output(cmd, stderr=subprocess.PIPE, env=currenv,
                                    # start new session to avoid hangs
                                    start_new_session=True,
                                    universal_newlines=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        if not safe:
            raise
        return None, None
    finally:
        if use_tmpfile:
            pass
            os.remove(tmpfile.name)
    env = parse_env(s)
    return env

def to_bool(x):
    """"Converts to a boolean in a semantically meaningful way."""
    if isinstance(x, bool):
        return x
    elif isinstance(x, str):
        return False if x.lower() in _FALSES else True
    else:
        return bool(x)

_FALSES = frozenset(['', '0', 'n', 'f', 'no', 'none', 'false'])

# mapping of shell name alises to keys in other lookup dictionaries.
CANON_SHELL_NAMES = {
    'bash': 'bash',
    '/bin/bash': 'bash',
    'zsh': 'zsh',
    '/bin/zsh': 'zsh',
    '/usr/bin/zsh': 'zsh',
    'cmd': 'cmd',
    'cmd.exe': 'cmd',
}

DEFAULT_ENVCMDS = {
    'bash': 'env',
    'zsh': 'env',
    'cmd': 'set',
}
DEFAULT_SOURCERS = {
    'bash': 'source',
    'zsh': 'source',
    'cmd': 'call',
}
DEFAULT_TMPFILE_EXT = {
    'bash': '.sh',
    'zsh': '.zsh',
    'cmd': '.bat',
}
DEFAULT_RUNCMD = {
    'bash': '-c',
    'zsh': '-c',
    'cmd': '/C',
}
DEFAULT_SETERRPREVCMD = {
    'bash': 'set -e',
    'zsh': 'set -e',
    'cmd': '@echo off',
}
DEFAULT_SETERRPOSTCMD = {
    'bash': '',
    'zsh': '',
    'cmd': 'if errorlevel 1 exit 1',
}

COMMAND = """
{seterrprevcmd}
{prevcmd}
echo __XONSH_ENV_BEG__
{envcmd}
echo __XONSH_ENV_END__
{postcmd}
{seterrpostcmd}
""".strip()

ENV_RE = re.compile('__XONSH_ENV_BEG__\n(.*)__XONSH_ENV_END__', flags=re.DOTALL)


def parse_env(s):
    """Parses the environment portion of string into a dict."""
    m = ENV_RE.search(s)
    if m is None:
        return {}
    g1 = m.group(1)
    items = [line.split('=', 1) for line in g1.splitlines() if '=' in line]
    env = dict(items)
    return env


def diff_dict(a, b):
    ret_dict = {}
    if ON_WINDOWS:
        # Windows var names are case insensitive
        a = {k.upper(): a[k] for k in a.keys()}
        b = {k.upper(): b[k] for k in b.keys()}

    # put in old values which got updated/removed
    for key, val in a.items():
        if key in b:
            if b[key] != val:
                # updated
                ret_dict[key] = (val, "->", b[key])
            else:
                # not changed
                pass
        else:
            # removed
            ret_dict[key] = (val, "->", "-")
    for key, val in b.items():
        if key not in a:
            # new
            ret_dict[key] = ("-", "->", val)
    return ret_dict