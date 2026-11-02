from importlib import metadata, resources

import aviscape_dsp


def test_version_matches_distribution_metadata() -> None:
    assert aviscape_dsp.__version__ == metadata.version("aviscape-dsp")


def test_package_is_marked_as_typed() -> None:
    assert resources.files(aviscape_dsp).joinpath("py.typed").is_file()
