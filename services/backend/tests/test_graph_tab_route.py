from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from orion_backend.core.database import get_orion_db
from orion_backend.main import app
from orion_backend.repositories.graph_tab_repository import GraphTabRepository

URL = "/api/v1/graph-tabs"


def tab(id_="a", name="Overview", layout=1, graphs=()):
    return {"id": id_, "name": name, "layout": layout, "graphs": list(graphs)}


def graph(id_="g1", channel="TPU/GPS/Location"):
    return {"id": id_, "channel": channel}


TABS = [
    tab("a", graphs=[graph("g1"), graph("g2", "BMS/Pack/SoC")]),
    tab("b", "Tab 2", layout=2),
]


@pytest.fixture
def stored(monkeypatch):
    """The saved tab list, kept in memory instead of OrionDB. `None` until a save."""
    store = {"tabs": None}

    async def get_tabs(self):
        return store["tabs"]

    async def save_tabs(self, tabs):
        store["tabs"] = tabs

    monkeypatch.setattr(GraphTabRepository, "get_tabs", get_tabs)
    monkeypatch.setattr(GraphTabRepository, "save_tabs", save_tabs)
    return store


@pytest.fixture
def client(stored):
    app.dependency_overrides[get_orion_db] = lambda: MagicMock()
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_with_nothing_saved_returns_empty_list(client):
    response = client.get(URL)
    assert response.status_code == 200
    assert response.json() == []


def test_save_then_get_returns_the_same_tabs_in_order(client, stored):
    response = client.put(URL, json=TABS)

    assert response.status_code == 200
    assert response.json() == TABS
    assert stored["tabs"] == TABS
    assert client.get(URL).json() == TABS


def test_second_save_replaces_the_first(client):
    client.put(URL, json=TABS)
    second = [tab("c", "Only tab", graphs=[graph("g9")])]

    assert client.put(URL, json=second).status_code == 200
    assert client.get(URL).json() == second


def test_saving_an_empty_list_clears_the_tabs(client):
    client.put(URL, json=TABS)
    assert client.put(URL, json=[]).status_code == 200
    assert client.get(URL).json() == []


def test_saved_tab_with_an_extra_field_still_loads(client, stored):
    # E.g. data saved before a field was removed from the schema.
    stored["tabs"] = [{**tab(graphs=[{**graph(), "unit": "m"}]), "color": "red"}]

    response = client.get(URL)

    assert response.status_code == 200
    assert response.json() == [tab(graphs=[graph()])]


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({"tabs": TABS}, id="not a list"),
        pytest.param([{**tab(), "color": "red"}], id="extra tab field"),
        pytest.param([tab(graphs=[{**graph(), "unit": "m"}])], id="extra graph field"),
        pytest.param([{"id": "a", "name": "n", "layout": 1}], id="missing field"),
        pytest.param([tab(id_=1)], id="id not a string"),
        pytest.param([tab(id_="")], id="empty id"),
        pytest.param([tab(id_="x" * 65)], id="long id"),
        pytest.param([tab(name="")], id="empty name"),
        pytest.param([tab(name="   ")], id="blank name"),
        pytest.param([tab(name="n" * 101)], id="long name"),
        pytest.param([tab(layout=3)], id="unknown layout"),
        pytest.param([tab(layout="1")], id="layout as string"),
        pytest.param([tab(layout=True)], id="layout as bool"),
        pytest.param([tab(graphs=[graph(channel="")])], id="empty channel"),
        pytest.param([tab(f"t{i}") for i in range(51)], id="51 tabs"),
        pytest.param([tab(graphs=[graph(f"g{i}") for i in range(51)])], id="51 graphs"),
        pytest.param([tab("a"), tab("a")], id="duplicate tab ids"),
        pytest.param(
            [tab("a", graphs=[graph("g")]), tab("b", graphs=[graph("g")])],
            id="duplicate graph ids across tabs",
        ),
    ],
)
def test_invalid_tabs_are_rejected_and_nothing_is_saved(client, body):
    client.put(URL, json=TABS)

    assert client.put(URL, json=body).status_code == 422
    assert client.get(URL).json() == TABS
