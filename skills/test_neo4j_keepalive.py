"""Staging tests for Neo4j Keep-Alive skill."""
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock


def _load_skill(sdk):
    spec = importlib.util.spec_from_file_location(
        "neo4j_keepalive_skill", Path(__file__).parent / "neo4j_keepalive.py"
    )
    mod = importlib.util.module_from_spec(spec)
    mod.sdk = sdk
    spec.loader.exec_module(mod)
    return mod


def _install_fake_src(monkeypatch, uri="neo4j+s://example.databases.neo4j.io", run_raises=None):
    """Inject fake src.config / src.epistemic modules so tests never touch a real driver."""
    calls = []

    class FakeStore:
        def run(self, cypher, **params):
            calls.append(cypher)
            if run_raises is not None:
                raise run_raises
            return [{"1": 1}]

    fake_src = types.ModuleType("src")
    fake_config = types.ModuleType("src.config")
    fake_config.NEO4J_URI = uri
    fake_epistemic = types.ModuleType("src.epistemic")
    fake_epistemic.Neo4jKnowledgeStore = FakeStore
    fake_src.config = fake_config
    fake_src.epistemic = fake_epistemic
    monkeypatch.setitem(sys.modules, "src", fake_src)
    monkeypatch.setitem(sys.modules, "src.config", fake_config)
    monkeypatch.setitem(sys.modules, "src.epistemic", fake_epistemic)
    return calls


def test_entry_point_defined():
    mod = _load_skill({"logger": MagicMock()})
    assert callable(mod.neo4j_keepalive)


def test_noop_when_unconfigured(monkeypatch):
    calls = _install_fake_src(monkeypatch, uri="")
    logger = MagicMock()
    mod = _load_skill({"logger": logger})
    result = mod.neo4j_keepalive()
    assert "skipped" in result
    assert calls == []
    logger.error.assert_not_called()


def test_success_pings_graph(monkeypatch):
    calls = _install_fake_src(monkeypatch)
    logger = MagicMock()
    mod = _load_skill({"logger": logger})
    result = mod.neo4j_keepalive()
    assert calls == ["RETURN 1"]
    assert "succeeded" in result
    logger.error.assert_not_called()


def test_failure_logs_error_pointing_at_aura_console(monkeypatch):
    _install_fake_src(monkeypatch, run_raises=RuntimeError("connection refused"))
    logger = MagicMock()
    mod = _load_skill({"logger": logger})
    result = mod.neo4j_keepalive()
    assert "FAILED" in result
    assert "connection refused" in result
    logger.error.assert_called_once()
    msg = logger.error.call_args[0][0]
    assert "Aura console" in msg
    assert "connection refused" in msg
