"""Lazy and self destructive container for speeding up module import."""
# Copyright 2015-2016, the xonsh developers. All rights reserved.

# Inspiration by https://github.com/xonsh/xonsh/blob/master/xonsh/lazyasd.py

# Original license:
# Copyright 2015-2016, the xonsh developers. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are
# permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright notice, this list of
#       conditions and the following disclaimer.
#
#    2. Redistributions in binary form must reproduce the above copyright notice, this list
#       of conditions and the following disclaimer in the documentation and/or other materials
#       provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE XONSH DEVELOPERS ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE XONSH DEVELOPERS OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are those of the
# authors and should not be interpreted as representing official policies, either expressed
# or implied, of the stakeholders of the xonsh project or the employers of xonsh developers.

from __future__ import absolute_import
from .utils import MutableMapping


# can't use MutableMapping only, because downstream (json.dumps and traitlets) tests for dict
# directly :-(
class LazyProxyDict(MutableMapping, dict):

    def __init__(self, load):
        """Dictionary like object that lazily loads its values via the load function

        Parameters
        ----------
        load : loader which returns the real dict.
        """
        self._lasdo = {
            'loaded': False,
            'load': load
        }

    def _lazy_obj(self):
        d = self._lasdo
        if d['loaded']:
            obj = d['obj']
        else:
            obj = d['load']()
            assert isinstance(obj, dict)
            d['obj'] = obj
            d['loaded'] = True
        return obj

    def __getitem__(self, key):
        d = self._lazy_obj()
        return d.__getitem__(key)

    def __setitem__(self, key, value):
        d = self._lazy_obj()
        d.__setitem__(key, value)

    def __delitem__(self, key):
        d = self._lazy_obj()
        d.__delitem__(key)

    def __iter__(self):
        for item in self._lazy_obj():
            yield item

    def __len__(self):
        return self._lazy_obj().__len__()

    # Implementation of "=="  is needed so that loading doesn't get triggered during the trait
    # setting when the KernelSpec instance is created.
    def __eq__(self, other):
        if self._lasdo['loaded']:
            return dict(self.items()) == dict(other.items())
        else:
            raise ValueError("Real values not yet loaded")
