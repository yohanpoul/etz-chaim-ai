"""Tests Teshuvah Writer — conversion faille → test de regression reel."""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sitra_achra.teshuvah_writer import (
    TeshuvahWriteResult,
    _make_class_suffix,
    _sanitize_name,
    process_teshuvah_records,
    store_teshuvah_in_db,
    write_regression_test,
)


def _make_record(
    module: str = "epistememory",
    flaw: str = "memoire corrompue par injection",
    severity: str = "anan",
    qliphah: str = "gamaliel",
    timestamp: float | None = None,
) -> dict:
    """Helper pour creer un TeshuvahRecord dict."""
    return {
        "module": module,
        "flaw_description": flaw,
        "severity": severity,
        "qliphah": qliphah,
        "regression_test": f"test_regression_{module}_{qliphah}",
        "stored": False,
        "timestamp": timestamp or time.time(),
    }


# ---------------------------------------------------------------------------
# Sanitize helpers
# ---------------------------------------------------------------------------


class TestSanitizeName:

    def test_basic(self):
        assert _sanitize_name("samael") == "samael"

    def test_spaces_and_special(self):
        assert _sanitize_name("foo bar-baz!") == "foo_bar_baz"

    def test_truncates_at_60(self):
        result = _sanitize_name("a" * 100)
        assert len(result) == 60

    def test_empty_string(self):
        assert _sanitize_name("") == "unknown"


class TestMakeClassSuffix:

    def test_format(self):
        record = _make_record(qliphah="samael", timestamp=1234567890.0)
        suffix = _make_class_suffix(record)
        assert "Samael" in suffix
        assert "567890" in suffix


# ---------------------------------------------------------------------------
# write_regression_test
# ---------------------------------------------------------------------------


class TestWriteRegressionTest:

    def test_writes_file(self, tmp_path):
        """Ecrit un fichier pytest valide."""
        record = _make_record(module="epistememory")

        with patch("sitra_achra.teshuvah_writer._PROJECT_ROOT", tmp_path):
            # Creer le dossier
            test_dir = tmp_path / "epistememory" / "tests"
            test_dir.mkdir(parents=True)

            result = write_regression_test(record)

        assert result.written is True
        assert result.error is None
        assert "epistememory/tests/test_regression_gamaliel_" in result.file_path

        # Verifier que le fichier est du Python valide
        full_path = tmp_path / result.file_path
        assert full_path.exists()

        import ast
        ast.parse(full_path.read_text())  # Ne doit pas lever d'exception

    def test_unknown_module_fails(self, tmp_path):
        """Module inconnu → erreur."""
        record = _make_record(module="inexistant")

        with patch("sitra_achra.teshuvah_writer._PROJECT_ROOT", tmp_path):
            result = write_regression_test(record)

        assert result.written is False
        assert "module inconnu" in result.error

    def test_idempotent_no_overwrite(self, tmp_path):
        """Ne doit pas ecraser un test existant."""
        record = _make_record(module="epistememory")

        with patch("sitra_achra.teshuvah_writer._PROJECT_ROOT", tmp_path):
            test_dir = tmp_path / "epistememory" / "tests"
            test_dir.mkdir(parents=True)

            # Premier appel → ecrit
            result1 = write_regression_test(record)
            assert result1.written is True

            # Deuxieme appel meme record → pas d'ecriture
            result2 = write_regression_test(record)
            assert result2.written is False
            assert "existe deja" in result2.error

    def test_creates_init_py(self, tmp_path):
        """Cree __init__.py si absent."""
        record = _make_record(module="selfmap")

        with patch("sitra_achra.teshuvah_writer._PROJECT_ROOT", tmp_path):
            test_dir = tmp_path / "selfmap" / "tests"
            test_dir.mkdir(parents=True)
            # Pas de __init__.py

            write_regression_test(record)

        assert (test_dir / "__init__.py").exists()

    def test_samael_template(self, tmp_path):
        """Qliphah samael → template rigidite."""
        record = _make_record(module="epistememory", qliphah="samael")

        with patch("sitra_achra.teshuvah_writer._PROJECT_ROOT", tmp_path):
            test_dir = tmp_path / "epistememory" / "tests"
            test_dir.mkdir(parents=True)

            result = write_regression_test(record)

        content = (tmp_path / result.file_path).read_text()
        assert "rigidite excessive" in content
        assert "Gevurah sans Chesed" in content

    def test_gamchicoth_template(self, tmp_path):
        """Qliphah gamchicoth → template expansion."""
        record = _make_record(module="autojudge", qliphah="gamchicoth")

        with patch("sitra_achra.teshuvah_writer._PROJECT_ROOT", tmp_path):
            test_dir = tmp_path / "autojudge" / "tests"
            test_dir.mkdir(parents=True)

            result = write_regression_test(record)

        content = (tmp_path / result.file_path).read_text()
        assert "expansion excessive" in content

    def test_sathariel_template(self, tmp_path):
        """Qliphah sathariel → template opacite."""
        record = _make_record(module="selfmap", qliphah="sathariel")

        with patch("sitra_achra.teshuvah_writer._PROJECT_ROOT", tmp_path):
            test_dir = tmp_path / "selfmap" / "tests"
            test_dir.mkdir(parents=True)

            result = write_regression_test(record)

        content = (tmp_path / result.file_path).read_text()
        assert "opacite" in content

    def test_unknown_qliphah_uses_default(self, tmp_path):
        """Qliphah inconnue → template generique."""
        record = _make_record(module="epistememory", qliphah="custom_evil")

        with patch("sitra_achra.teshuvah_writer._PROJECT_ROOT", tmp_path):
            test_dir = tmp_path / "epistememory" / "tests"
            test_dir.mkdir(parents=True)

            result = write_regression_test(record)

        content = (tmp_path / result.file_path).read_text()
        assert "custom_evil" in content
        assert result.written is True

    def test_generated_test_has_docstrings(self, tmp_path):
        """Le test genere contient la documentation de la faille.

        Note Sprint 1.1 : la source citee differe selon la categorie
        ontologique Vital EC 49 (Yoma 86b pour Klipat Nogah / Birur,
        Vital EC 49 + Tanya ch. 6 pour Klippot HaTeme'ot / Confinement).
        Ce test verifie que la source doctrinale appropriee est presente.
        """
        flaw = "injection SQL via le champ content de epistememory"
        # severity='nogah' = Klipat Nogah = template Birur (Yoma 86b)
        record_nogah = _make_record(module="epistememory", flaw=flaw, severity="nogah")

        with patch("sitra_achra.teshuvah_writer._PROJECT_ROOT", tmp_path):
            test_dir = tmp_path / "epistememory" / "tests"
            test_dir.mkdir(parents=True)
            result_nogah = write_regression_test(record_nogah)

        content_nogah = (tmp_path / result_nogah.file_path).read_text()
        assert "injection SQL" in content_nogah
        assert "Yoma 86b" in content_nogah  # Birur source
        assert "Sitra Achra" in content_nogah

    def test_containment_test_has_haTeme_ot_sources(self, tmp_path):
        """Pour HaTeme'ot, le test cite Vital EC 49 + Tanya ch. 6."""
        flaw = "injection SQL via le champ content de epistememory"
        # severity='anan' = Klipa HaTemeah = template Containment
        record = _make_record(module="epistememory", flaw=flaw, severity="anan")

        with patch("sitra_achra.teshuvah_writer._PROJECT_ROOT", tmp_path):
            test_dir = tmp_path / "epistememory" / "tests"
            test_dir.mkdir(parents=True)
            result = write_regression_test(record)

        content = (tmp_path / result.file_path).read_text()
        assert "injection SQL" in content
        assert "Vital EC 49" in content
        assert "Tanya ch. 6" in content
        assert "containment" in content.lower() or "confinement" in content.lower()
        assert "Sitra Achra" in content


# ---------------------------------------------------------------------------
# process_teshuvah_records
# ---------------------------------------------------------------------------


class TestProcessTeshuvahRecords:

    def test_processes_multiple(self, tmp_path):
        """Traite plusieurs records."""
        records = [
            _make_record(module="epistememory", qliphah="samael", timestamp=1000001.0),
            _make_record(module="selfmap", qliphah="sathariel", timestamp=1000002.0),
        ]

        with patch("sitra_achra.teshuvah_writer._PROJECT_ROOT", tmp_path):
            for mod in ("epistememory", "selfmap"):
                (tmp_path / mod / "tests").mkdir(parents=True)

            results = process_teshuvah_records(records)

        assert len(results) == 2
        assert all(r.written for r in results)

    def test_empty_list(self):
        """Liste vide → liste vide."""
        results = process_teshuvah_records([])
        assert results == []

    def test_partial_failure(self, tmp_path):
        """Un module inconnu ne bloque pas les autres."""
        records = [
            _make_record(module="epistememory", timestamp=2000001.0),
            _make_record(module="inexistant", timestamp=2000002.0),
        ]

        with patch("sitra_achra.teshuvah_writer._PROJECT_ROOT", tmp_path):
            (tmp_path / "epistememory" / "tests").mkdir(parents=True)

            results = process_teshuvah_records(records)

        written = [r for r in results if r.written]
        failed = [r for r in results if not r.written]
        assert len(written) == 1
        assert len(failed) == 1


# ---------------------------------------------------------------------------
# TeshuvahWriteResult
# ---------------------------------------------------------------------------


class TestTeshuvahWriteResult:

    def test_to_dict(self):
        r = TeshuvahWriteResult(
            module="epistememory",
            file_path="epistememory/tests/test_regression_samael_123456.py",
            test_name="test_regression_samael_123456.py",
            written=True,
        )
        d = r.to_dict()
        assert d["module"] == "epistememory"
        assert d["written"] is True
        assert "file_path" in d


# ---------------------------------------------------------------------------
# store_teshuvah_in_db
# ---------------------------------------------------------------------------


class TestStoreTeshuvahInDb:

    def test_stores_written_results(self):
        """Stocke en epistememory les Teshuvah ecrits."""
        results = [
            TeshuvahWriteResult(
                module="epistememory",
                file_path="epistememory/tests/test_reg.py",
                test_name="test_reg.py",
                written=True,
            ),
        ]
        mock_conn = MagicMock()
        mock_conn.closed = False  # evite la branche retry de pool.get_conn
        mock_cur = MagicMock()
        # `with conn.cursor() as cur:` — __enter__ doit retourner mock_cur
        mock_cur.__enter__.return_value = mock_cur
        mock_cur.__exit__.return_value = False
        mock_conn.cursor.return_value = mock_cur

        with patch("psycopg2.connect", return_value=mock_conn):
            # Passer un db_url de test : le default (etz_chaim) est refuse
            # par la garde anti-prod de pool.init_pool sous pytest.
            stored = store_teshuvah_in_db(results, db_url="postgresql://localhost/test")

        assert stored == 1
        mock_cur.execute.assert_called_once()
        sql = mock_cur.execute.call_args[0][0]
        assert "INSERT INTO epistememory" in sql

    def test_skips_if_none_written(self):
        """Rien d'ecrit → pas de stockage."""
        results = [
            TeshuvahWriteResult(
                module="x", file_path="", test_name="", written=False
            ),
        ]
        stored = store_teshuvah_in_db(results)
        assert stored == 0

    def test_graceful_on_db_failure(self):
        """DB indisponible → gracieux."""
        results = [
            TeshuvahWriteResult(
                module="m", file_path="p", test_name="t", written=True
            ),
        ]
        with patch("psycopg2.connect", side_effect=Exception("no db")):
            stored = store_teshuvah_in_db(results)
        assert stored == 0
