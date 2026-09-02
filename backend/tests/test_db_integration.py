"""Runs only when database credentials are present in the environment
(DB_HOST, DB_USER, DB_PASS, DB_NAME, DB_PORT as read by config.py)."""
import os

import pytest

import flask_reporting as fr

pytestmark = pytest.mark.skipif(not os.environ.get("DB_PASS"), reason="no database credentials in environment")


def test_pmid_listed_second_for_its_neurons_resolves_all_of_them():
    # DeFelipe neurons list 26762857, 26850576, 27832100 - the search service finds none by 26850576
    assert len(fr.pmid_neuron_ids([26850576])) == 288


def test_neuron_with_two_pmids_is_found_by_either():
    assert 1 in fr.pmid_neuron_ids([12204204])
    assert 1 in fr.pmid_neuron_ids([12902394])


def test_unknown_pmid_resolves_to_no_neurons():
    assert fr.pmid_neuron_ids([999999999]) == set()


def test_empty_pmid_list_resolves_to_no_neurons_without_querying():
    assert fr.pmid_neuron_ids([]) == set()
