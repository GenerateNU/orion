from temp_orion.signals_catalog import SIGNALS


def test_signals_have_required_fields():
    required = {
        "raw_tag",
        "name",
        "display_name",
        "description",
        "unit",
    }

    for signal in SIGNALS:
        assert required == set(signal.keys())


def test_raw_tags_are_unique():
    raw_tags = [signal["raw_tag"] for signal in SIGNALS]

    assert len(raw_tags) == len(set(raw_tags))


def test_names_are_unique():
    names = [signal["name"] for signal in SIGNALS]

    assert len(names) == len(set(names))