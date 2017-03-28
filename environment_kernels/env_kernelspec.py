# coding: utf-8
"""Common function to deal with virtual environments"""
from __future__ import absolute_import

from jupyter_client.kernelspec import KernelSpec
from traitlets import default

_nothing = object()

class EnvironmentLoadingKernelSpec(KernelSpec):
    """A KernelSpec which loads `env` by activating the virtual environment"""

    _loader = None
    _env = _nothing

    @property
    def env(self):
        if self._env is _nothing:
            if self._loader:
                try:
                    self._env = self._loader()
                except:
                    self._env = {}
        return self._env

    def __init__(self, loader, **kwargs):
        self._loader = loader
        super(EnvironmentLoadingKernelSpec, self).__init__(**kwargs)


    def to_dict(self):
        d = dict(argv=self.argv,
                 # Do not trigger the loading
                 #env=self.env,
                 display_name=self.display_name,
                 language=self.language,
                )

        return d

