from importlib import metadata, resources

import aviscape_api


def test_version_matches_distribution_metadata() -> None:
    assert aviscape_api.__version__ == metadata.version("aviscape-api")


def test_package_is_marked_as_typed() -> None:
    assert resources.files(aviscape_api).joinpath("py.typed").is_file()
