from importlib import metadata, resources

import aviscape_contracts


def test_version_matches_distribution_metadata() -> None:
    assert aviscape_contracts.__version__ == metadata.version("aviscape-contracts")


def test_package_is_marked_as_typed() -> None:
    assert resources.files(aviscape_contracts).joinpath("py.typed").is_file()
