# coding: utf-8
"""Compatibility tricks for Python 3. Mainly to do with unicode."""

# https://github.com/ipython/ipython/blob/master/IPython/utils/py3compat.py
# Parts of it stolen from IPython under the 3-Clause BSD:
#
# =============================
#  The IPython licensing terms
# =============================
#
# IPython is licensed under the terms of the Modified BSD License (also known as
# New or Revised or 3-Clause BSD), as follows:
#
# - Copyright (c) 2008-2014, IPython Development Team
# - Copyright (c) 2001-2007, Fernando Perez <fernando.perez@colorado.edu>
# - Copyright (c) 2001, Janko Hauser <jhauser@zscout.de>
# - Copyright (c) 2001, Nathaniel Gray <n8gray@caltech.edu>
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
#
# Redistributions in binary form must reproduce the above copyright notice, this
# list of conditions and the following disclaimer in the documentation and/or
# other materials provided with the distribution.
#
# Neither the name of the IPython Development Team nor the names of its
# contributors may be used to endorse or promote products derived from this
# software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.



import os
import sys
import platform

if sys.version_info[0] >= 3:
    PY3 = True
    FileNotFoundError = FileNotFoundError
    from collections.abc import MutableMapping as MutableMapping

else:
    PY3 = False
    FileNotFoundError = IOError
    from collections import MutableMapping as MutableMapping

PY2 = not PY3

ON_DARWIN = platform.system() == 'Darwin'
ON_LINUX = platform.system() == 'Linux'
ON_WINDOWS = platform.system() == 'Windows'

PYTHON_VERSION_INFO = sys.version_info[:3]
ON_ANACONDA = any(s in sys.version for s in {'Anaconda', 'Continuum'})

ON_POSIX = (os.name == 'posix')

try:
    import conda.config
    HAVE_CONDA = True
except ImportError:
    HAVE_CONDA = False
