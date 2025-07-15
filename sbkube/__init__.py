# type: ignore
try:
    from importlib.metadata import version

    __version__ = version("sbkube")
except ImportError:
    from importlib_metadata import version  # Python <3.8

    __version__ = version("sbkube")
