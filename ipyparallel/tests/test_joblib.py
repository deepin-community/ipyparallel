import warnings
from unittest import mock

import pytest

import ipyparallel as ipp

from .clienttest import ClusterTestCase, add_engines

try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from joblib import Parallel, delayed

        from ipyparallel.client._joblib import IPythonParallelBackend  # noqa
except (ImportError, TypeError):
    have_joblib = False
else:
    have_joblib = True


def neg(x):
    return -1 * x


class TestJobLib(ClusterTestCase):
    def setup_method(self):
        if not have_joblib:
            pytest.skip("Requires joblib >= 0.10")
        super().setup_method()
        add_engines(1, total=True)

    def test_default_backend(self):
        """ipyparallel.register_joblib_backend() registers default backend"""
        ipp.register_joblib_backend()
        with mock.patch.object(ipp.Client, "__new__", lambda *a, **kw: self.client):
            p = Parallel(backend='ipyparallel')
            assert p._backend._view.client is self.client

    def test_register_backend(self):
        view = self.client.load_balanced_view()
        view.register_joblib_backend('view')
        p = Parallel(backend='view')
        assert p._backend._view is view

    def test_joblib_backend(self):
        view = self.client.load_balanced_view()
        view.register_joblib_backend('view')
        p = Parallel(backend='view')
        result = p(delayed(neg)(i) for i in range(10))
        assert result == [neg(i) for i in range(10)]
