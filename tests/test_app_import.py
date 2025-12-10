import importlib


def test_api_import():
    mod = importlib.import_module("api.main")
    importlib.reload(mod)
    assert hasattr(mod, "app")
