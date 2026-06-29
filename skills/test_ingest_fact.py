"""Staging test for Ingest Fact skill."""
import importlib.util
import logging
from pathlib import Path
from unittest.mock import MagicMock


def _make_sdk():
    class MockDB:
        def execute(self, sql, p=None): return []
        def fetchone(self, sql, p=None): return None
        def fetchall(self, sql, p=None): return []
    class MockFS:
        def read(self, p): return ""
        def write(self, p, c): return True
        def exists(self, p): return True
        def list_dir(self, p): return []
    class MockMemory:
        def add_memory(self, t, m=None): pass
        def query_memories(self, q, n=5): return []
        def log_episodic_memory(self, *a, **kw): pass
        def log_episode(self, *a, **kw): pass
    class MockSwarm:
        def query_agent(self, a, p, **kw): return "mock response"
        def get_constitution(self): return []
        def log_deliberation(self, **kw): pass
        def parse_action(self, a): return None, {}, "mock"
        def execute_skill(self, s, a, **kw): return {"success": True, "result": "mock"}
        def parse_critic_response(self, r): return 1, "approved"
        def validate_action(self, a): pass
        def get_pending_messages(self, a): return []
        def mark_message_processed(self, mid): pass
        def send_message(self, *a): pass
        def get_curiosity_topics(self): return []
        def get_active_goals(self): return []
    class MockLogger:
        def info(self, *a, **kw): pass
        def error(self, *a, **kw): pass
        def warning(self, *a, **kw): pass
        def debug(self, *a, **kw): pass
    return {
        "db": MockDB(), "fs": MockFS(), "memory": MockMemory(),
        "swarm": MockSwarm(), "logger": MockLogger(),
        "goals": MagicMock(), "drives": MagicMock(),
        "self_model": MagicMock(), "explorer": MagicMock(),
        "codebase": MagicMock(), "sandbox": MagicMock(),
        "documents": MagicMock(), "replication": MagicMock(),
        "layered_cognition": MagicMock(),
    }


def test_skill_entry_point_defined():
    """Verify skill file loads and entry point is defined."""
    spec = importlib.util.spec_from_file_location(
        "skill", Path(__file__).parent / "ingest_fact.py"
    )
    mod = importlib.util.module_from_spec(spec)
    mod.sdk = _make_sdk()
    spec.loader.exec_module(mod)
    assert hasattr(mod, "run")
    assert callable(getattr(mod, "run"))
