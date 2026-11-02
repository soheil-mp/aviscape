from importlib import metadata, resources

import aviscape_edge


def test_version_matches_distribution_metadata() -> None:
    assert aviscape_edge.__version__ == metadata.version("aviscape-edge")


def test_package_is_marked_as_typed() -> None:
    assert resources.files(aviscape_edge).joinpath("py.typed").is_file()
