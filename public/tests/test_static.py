import pytest
from django.contrib.staticfiles.finders import find


@pytest.mark.functional
@pytest.mark.parametrize(
    "static_path",
    [
        "vendor/bootstrap/bootstrap.min.css",
        "vendor/bootstrap/bootstrap.bundle.min.js",
        "css/app.css",
    ],
)
def test_static_asset_is_discoverable(static_path):
    assert find(static_path) is not None
