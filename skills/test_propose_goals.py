"""Staging tests for Propose Goals skill (V2-T1b)."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import MagicMock


def _make_sdk(
    max_open="3",
    open_count=0,
    llm_response="[]",
    curiosity_topics=None,
    llm_raises=False,
):
    class MockDB:
        def __init__(self):
            self.queries = []

        def query(self, sql, params=()):
            self.queries.append(sql)
            if "goal_proposal.max_open_proposals" in sql:
                return [{"config_value": max_open}] if max_open is not None else []
            if "FROM goals" in sql:
                return [{"type": "long", "description": "Existing active goal"}]
            if "FROM goal_proposals" in sql:
                return [{"description": "Already pending proposal"}] * open_count
            return []

    class MockMemory:
        def __init__(self):
            self.episodes = []

        def get_active_curiosity_topics(self, limit=5):
            return curiosity_topics if curiosity_topics is not None else ["rust async runtimes"]

        def get_recent_episodic_memories(self, limit=5):
            return [("user", "hello", "2026-07-04T00:00:00")]

        def log_episodic_memory(self, speaker, message_content, context_type="background_thought"):
            self.episodes.append((speaker, message_content, context_type))

    class MockDrives:
        def get_curiosity_vector(self):
            return ["fallback topic"]

    class MockSwarm:
        def __init__(self):
            self.calls = []

        def query_agent(self, agent_id, prompt, **kwargs):
            self.calls.append((agent_id, prompt))
            if llm_raises:
                raise RuntimeError("endpoint unreachable")
            return llm_response

    class MockGoals:
        def __init__(self):
            self.proposed = []

        def propose_goal(self, type, description, confidence_score, source_reason):
            self.proposed.append(
                {
                    "type": type,
                    "description": description,
                    "confidence_score": confidence_score,
                    "source_reason": source_reason,
                }
            )
            return len(self.proposed)

    return {
        "db": MockDB(),
        "memory": MockMemory(),
        "drives": MockDrives(),
        "swarm": MockSwarm(),
        "goals": MockGoals(),
        "logger": MagicMock(),
        "fs": MagicMock(),
        "self_model": MagicMock(),
    }


def _load_skill(sdk):
    spec = importlib.util.spec_from_file_location(
        "propose_goals_skill", Path(__file__).parent / "propose_goals.py"
    )
    mod = importlib.util.module_from_spec(spec)
    mod.sdk = sdk
    spec.loader.exec_module(mod)
    return mod


def test_entry_point_defined():
    sdk = _make_sdk()
    mod = _load_skill(sdk)
    assert callable(mod.propose_goals)


def test_generates_proposals_from_llm_json():
    llm_response = json.dumps(
        [
            {
                "type": "short",
                "description": "Benchmark tokio vs async-std schedulers",
                "confidence": 0.8,
                "source_reason": "Curiosity topic: rust async runtimes",
            },
            {
                "type": "long",
                "description": "Write an internal guide on async runtime tradeoffs",
                "confidence": 0.6,
                "source_reason": "Follow-up to exploration thread",
            },
        ]
    )
    sdk = _make_sdk(llm_response=llm_response)
    mod = _load_skill(sdk)
    result = mod.propose_goals()

    assert len(sdk["goals"].proposed) == 2
    first = sdk["goals"].proposed[0]
    assert first["type"] == "short"
    assert first["description"] == "Benchmark tokio vs async-std schedulers"
    assert first["confidence_score"] == 0.8
    assert first["source_reason"] == "Curiosity topic: rust async runtimes"
    # Curiosity context must reach the proposer prompt
    assert "rust async runtimes" in sdk["swarm"].calls[0][1]
    # Generation logs a background thought for the episodic record
    assert len(sdk["memory"].episodes) == 1
    assert sdk["memory"].episodes[0][2] == "background_thought"
    assert "Generated 2 goal proposal(s)" in result


def test_parse_failure_is_tolerated():
    sdk = _make_sdk(llm_response="I believe we should pursue several interesting things.")
    mod = _load_skill(sdk)
    result = mod.propose_goals()
    assert sdk["goals"].proposed == []
    assert "no parseable JSON array" in result


def test_invalid_json_is_tolerated():
    sdk = _make_sdk(llm_response='[{"type": "short", "description": broken}]')
    mod = _load_skill(sdk)
    result = mod.propose_goals()
    assert sdk["goals"].proposed == []
    assert "not valid JSON" in result


def test_llm_error_is_tolerated():
    sdk = _make_sdk(llm_raises=True)
    mod = _load_skill(sdk)
    result = mod.propose_goals()
    assert sdk["goals"].proposed == []
    assert "LLM call error" in result


def test_cap_suppresses_generation():
    sdk = _make_sdk(open_count=3)
    mod = _load_skill(sdk)
    result = mod.propose_goals()
    # No LLM call, no inserts while the review queue is full
    assert sdk["swarm"].calls == []
    assert sdk["goals"].proposed == []
    assert "Skipped goal proposal generation" in result


def test_zero_cap_disables_generation():
    sdk = _make_sdk(max_open="0")
    mod = _load_skill(sdk)
    result = mod.propose_goals()
    assert sdk["swarm"].calls == []
    assert sdk["goals"].proposed == []
    assert "disabled" in result


def test_missing_config_defaults_to_three():
    llm_response = json.dumps(
        [
            {"type": "short", "description": f"Goal {i}", "confidence": 0.5, "source_reason": "r"}
            for i in range(5)
        ]
    )
    sdk = _make_sdk(max_open=None, llm_response=llm_response)
    mod = _load_skill(sdk)
    mod.propose_goals()
    assert len(sdk["goals"].proposed) == 3


def test_invalid_candidates_skipped_and_confidence_clamped():
    llm_response = json.dumps(
        [
            {"type": "urgent", "description": "Bad type", "confidence": 0.5, "source_reason": "r"},
            {"type": "short", "description": "", "confidence": 0.5, "source_reason": "r"},
            "not even a dict",
            {"type": "stretch", "description": "Valid goal", "confidence": 7, "source_reason": ""},
        ]
    )
    sdk = _make_sdk(llm_response=llm_response)
    mod = _load_skill(sdk)
    result = mod.propose_goals()
    assert len(sdk["goals"].proposed) == 1
    proposed = sdk["goals"].proposed[0]
    assert proposed["type"] == "stretch"
    assert proposed["confidence_score"] == 1.0
    assert proposed["source_reason"] == "Subconscious proposal from idle reflection."
    assert "skipped 3 invalid candidate(s)" in result


def test_open_slots_limit_inserts():
    llm_response = json.dumps(
        [
            {"type": "short", "description": f"Goal {i}", "confidence": 0.5, "source_reason": "r"}
            for i in range(4)
        ]
    )
    sdk = _make_sdk(open_count=2, llm_response=llm_response)
    mod = _load_skill(sdk)
    mod.propose_goals()
    # cap 3, 2 already pending -> only one slot left
    assert len(sdk["goals"].proposed) == 1


def test_curiosity_falls_back_to_drive_vector():
    sdk = _make_sdk(curiosity_topics=[], llm_response="[]")
    mod = _load_skill(sdk)
    mod.propose_goals()
    assert "fallback topic" in sdk["swarm"].calls[0][1]
