"""Tests du validateur de fichiers YAML Sifrei Yesod."""

import yaml
import pytest

from sifrei_yesod.pipeline.validator import validate_perek, validate_file
from .conftest import FIXTURE_PEREK_YAML


def test_valid_perek():
    """Un perek YAML valide passe sans erreur."""
    data = yaml.safe_load(FIXTURE_PEREK_YAML)
    errors = validate_perek(data)
    assert errors == [], f"Erreurs inattendues: {errors}"


def test_invalid_id_format():
    """Un ID mal formé produit une erreur de schema."""
    data = yaml.safe_load(FIXTURE_PEREK_YAML)
    data["assertions"][0]["id"] = "bad-id"
    errors = validate_perek(data)
    assert any("id" in e and "match" in e.lower() for e in errors)


def test_missing_required_field():
    """Un champ obligatoire manquant produit une erreur."""
    data = yaml.safe_load(FIXTURE_PEREK_YAML)
    del data["assertions"][0]["assertion"]
    errors = validate_perek(data)
    assert any("assertion" in e for e in errors)


def test_invalid_assertion_type():
    """Un type d'assertion invalide produit une erreur."""
    data = yaml.safe_load(FIXTURE_PEREK_YAML)
    data["assertions"][0]["type"] = "type_inexistant"
    errors = validate_perek(data)
    assert any("type" in e.lower() for e in errors)


def test_duplicate_assertion_id():
    """Des IDs en double sont détectés."""
    data = yaml.safe_load(FIXTURE_PEREK_YAML)
    data["assertions"].append(data["assertions"][0].copy())
    errors = validate_perek(data)
    assert any("duplicate" in e for e in errors)


def test_invalid_assertion_source_ref(capsys):
    """Une relation référençant une assertion inter-perek produit un warning."""
    data = yaml.safe_load(FIXTURE_PEREK_YAML)
    data["relations"][0]["assertions_source"] = ["INEXISTANT-001"]
    errors = validate_perek(data)
    assert errors == [], "Les xref inter-perek ne doivent pas être des erreurs"
    captured = capsys.readouterr()
    assert "INEXISTANT-001" in captured.err


def test_invalid_principle_source_ref(capsys):
    """Un principe référençant une assertion inter-perek produit un warning."""
    data = yaml.safe_load(FIXTURE_PEREK_YAML)
    data["principes_generatifs"][0]["source_assertions"] = ["NOPE-001"]
    errors = validate_perek(data)
    assert errors == [], "Les xref inter-perek ne doivent pas être des erreurs"
    captured = capsys.readouterr()
    assert "NOPE-001" in captured.err


def test_empty_yaml(tmp_path):
    """Un fichier YAML vide produit une erreur."""
    f = tmp_path / "empty.yaml"
    f.write_text("")
    ok, errors = validate_file(f)
    assert not ok
    assert any("vide" in e.lower() for e in errors)


def test_empty_assertions():
    """Un perek sans assertions produit une erreur de schema."""
    data = yaml.safe_load(FIXTURE_PEREK_YAML)
    data["assertions"] = []
    errors = validate_perek(data)
    assert len(errors) > 0
