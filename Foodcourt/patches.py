"""Project-level patches for third-party framework bugs.

Django 4.2.x is incompatible with Python 3.14 in ``BaseContext.__copy__``
(Django issue #35844): ``copy(super())`` returns a ``super`` proxy without a
``__dict__``, so ``BaseContext``/``Context``/``RequestContext`` instances can no
longer be copied. The Django test client copies the context of every rendered
template, so this crashes email rendering (and any template render) under the
test runner. Django 5.x ships the official fix; we mirror it here for 4.2.x.
If Django is upgraded to a version containing the fix, this becomes a harmless
no-op override.
"""
from copy import copy as _copy

from django.template.context import BaseContext


def _patched_context_copy(self):
    duplicate = BaseContext()
    duplicate.__class__ = self.__class__
    duplicate.__dict__ = _copy(self.__dict__)
    duplicate.dicts = self.dicts[:]
    return duplicate


BaseContext.__copy__ = _patched_context_copy
