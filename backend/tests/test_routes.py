import json

import pytest

import flask_reporting as fr


@pytest.fixture
def client():
    fr.app.config["TESTING"] = True
    return fr.app.test_client()


def payload(**neuron_filters):
    return {"neuron": neuron_filters, "ageWeightOperators": {}, "ageWeightOperations": {}}


def test_neuron_ids_route_returns_resolved_ids_as_json_list(client, monkeypatch):
    monkeypatch.setattr(fr, "resolve_neuron_ids", lambda p: [1, 2])

    response = client.post("/neuronIds", json=payload(pmid=["26850576"]))

    assert response.status_code == 200
    assert response.get_json() == [1, 2]


def test_count_route_with_pmid_counts_resolved_ids(client, monkeypatch):
    monkeypatch.setattr(fr, "resolve_neuron_ids", lambda p: [1, 2, 3])

    response = client.post("/count", json=payload(pmid=["26850576"]))

    assert response.status_code == 200
    assert response.get_json() == 3


def test_count_route_without_pmid_proxies_search_service_count(client, monkeypatch):
    def never(*a, **k):
        raise AssertionError("ids must not be resolved for a plain count")

    monkeypatch.setattr(fr, "resolve_neuron_ids", never)
    monkeypatch.setattr(fr, "search_service_count", lambda p: 298339)

    response = client.post("/count", json=payload(archive=["DeFelipe"]))

    assert response.status_code == 200
    assert response.get_json() == 298339


def test_report_generation_uses_the_resolver_for_neuron_selection(monkeypatch):
    seen = {}
    monkeypatch.setattr(fr, "resolve_neuron_ids", lambda p: [11, 12])
    monkeypatch.setattr(fr, "getNeuronInfoForGroups", lambda chunk: seen.setdefault("chunk", chunk))

    fr.getChunkedNeuronData("Groups", payload(pmid=["26850576"]), "stamp")

    assert seen["chunk"] == [11, 12]
