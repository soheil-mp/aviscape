from importlib import metadata, resources

import aviscape_synth


def test_version_matches_distribution_metadata() -> None:
    assert aviscape_synth.__version__ == metadata.version("aviscape-synth")


def test_package_is_marked_as_typed() -> None:
    assert resources.files(aviscape_synth).joinpath("py.typed").is_file()
