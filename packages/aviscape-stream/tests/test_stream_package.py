from importlib import metadata, resources

import aviscape_stream


def test_version_matches_distribution_metadata() -> None:
    assert aviscape_stream.__version__ == metadata.version("aviscape-stream")


def test_package_is_marked_as_typed() -> None:
    assert resources.files(aviscape_stream).joinpath("py.typed").is_file()
