"""Neuron selection: PMID filters are resolved from the database because the search
service indexes only one PMID per neuron (and sometimes the wrong one)."""
import pytest

import flask_reporting as fr


def payload(**neuron_filters):
    return {"neuron": neuron_filters, "ageWeightOperators": {}, "ageWeightOperations": {}}


def never_called(*args, **kwargs):
    raise AssertionError("should not have been called")


def test_pmid_only_filter_is_resolved_from_database_alone(monkeypatch):
    monkeypatch.setattr(fr, "pmid_neuron_ids", lambda pmids: {3, 1, 2})
    monkeypatch.setattr(fr, "search_service_neuron_ids", never_called)

    assert fr.resolve_neuron_ids(payload(pmid=["26850576"])) == [1, 2, 3]


def test_pmid_with_other_filters_intersects_database_with_search_service(monkeypatch):
    seen = {}

    def fake_search(p):
        seen["payload"] = p
        return ["2", "3", "4"]

    monkeypatch.setattr(fr, "pmid_neuron_ids", lambda pmids: {1, 2, 3})
    monkeypatch.setattr(fr, "search_service_neuron_ids", fake_search)

    result = fr.resolve_neuron_ids(payload(pmid=["26850576"], archive=["DeFelipe"]))

    assert result == [2, 3]
    assert seen["payload"]["neuron"] == {"archive": ["DeFelipe"]}


def test_without_pmid_filter_search_service_result_is_used_as_is(monkeypatch):
    monkeypatch.setattr(fr, "pmid_neuron_ids", never_called)
    monkeypatch.setattr(fr, "search_service_neuron_ids", lambda p: ["6", "5"])

    assert fr.resolve_neuron_ids(payload(archive=["DeFelipe"])) == [6, 5]


def test_empty_pmid_list_counts_as_no_pmid_filter(monkeypatch):
    monkeypatch.setattr(fr, "pmid_neuron_ids", never_called)
    monkeypatch.setattr(fr, "search_service_neuron_ids", lambda p: ["7"])

    assert fr.resolve_neuron_ids(payload(pmid=[], archive=["DeFelipe"])) == [7]


def test_resolving_does_not_modify_the_callers_payload(monkeypatch):
    monkeypatch.setattr(fr, "pmid_neuron_ids", lambda pmids: {1})
    monkeypatch.setattr(fr, "search_service_neuron_ids", lambda p: ["1"])
    p = payload(pmid=["26850576"], archive=["DeFelipe"])

    fr.resolve_neuron_ids(p)

    assert p["neuron"] == {"pmid": ["26850576"], "archive": ["DeFelipe"]}


def test_pmid_values_are_passed_to_the_database_as_integers(monkeypatch):
    seen = {}
    monkeypatch.setattr(fr, "pmid_neuron_ids", lambda pmids: seen.setdefault("pmids", pmids) and set())

    fr.resolve_neuron_ids(payload(pmid=["26850576", "-42", "not a pmid", ""]))

    assert seen["pmids"] == [26850576, -42]
