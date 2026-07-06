"""Staging test for GitHub Integration skill."""
import importlib.util
import logging
from pathlib import Path
from unittest.mock import MagicMock


def _make_sdk():
    mock_gh = MagicMock()
    mock_gh.list_open_issues.return_value = [{"number": 1, "title": "Test issue"}]
    mock_gh.get_issue.return_value = {"number": 5, "title": "Bug"}
    mock_gh.create_issue.return_value = {"number": 10}
    mock_gh.add_comment.return_value = {"id": 99}
    mock_gh.close_issue.return_value = {"state": "closed"}
    mock_gh.create_pr.return_value = {"number": 11}
    mock_gh.get_pr.return_value = {"number": 12, "title": "PR"}
    mock_gh.get_pr_diff.return_value = [{"filename": "a.py", "patch": "@@ -1 +1 @@"}]
    mock_gh.merge_pr.return_value = {"merged": True}
    mock_gh.update_issue.return_value = {"number": 8, "title": "Updated"}
    mock_gh.create_label.return_value = {"name": "triage"}
    return {
        "github": mock_gh,
        "logger": logging.getLogger("test"),
    }


def _load_skill():
    spec = importlib.util.spec_from_file_location(
        "github_integration", Path(__file__).parent / "github_integration.py"
    )
    mod = importlib.util.module_from_spec(spec)
    mod.sdk = _make_sdk()
    spec.loader.exec_module(mod)
    return mod


def test_skill_entry_point_defined():
    mod = _load_skill()
    assert hasattr(mod, "run")
    assert callable(mod.run)


def test_list_open_issues():
    mod = _load_skill()
    result = mod.run(action="list_open_issues", repo="owner/repo")
    mod.sdk["github"].list_open_issues.assert_called_once_with("owner/repo", label=None)
    assert result == [{"number": 1, "title": "Test issue"}]


def test_get_issue():
    mod = _load_skill()
    result = mod.run(action="get_issue", repo="owner/repo", number=5)
    mod.sdk["github"].get_issue.assert_called_once_with("owner/repo", 5)
    assert result["number"] == 5


def test_create_issue():
    mod = _load_skill()
    result = mod.run(action="create_issue", repo="owner/repo", title="New bug", body="Details")
    mod.sdk["github"].create_issue.assert_called_once_with("owner/repo", "New bug", "Details", None)
    assert result["number"] == 10


def test_add_comment():
    mod = _load_skill()
    result = mod.run(action="add_comment", repo="owner/repo", number=7, body="Nice work")
    mod.sdk["github"].add_comment.assert_called_once_with("owner/repo", 7, "Nice work")
    assert result["id"] == 99


def test_close_issue():
    mod = _load_skill()
    result = mod.run(action="close_issue", repo="owner/repo", number=31)
    mod.sdk["github"].close_issue.assert_called_once_with("owner/repo", 31)
    assert result["state"] == "closed"


def test_update_issue():
    mod = _load_skill()
    result = mod.run(action="update_issue", repo="owner/repo", number=8, title="Updated", labels=["bug"])
    mod.sdk["github"].update_issue.assert_called_once_with(
        "owner/repo", 8, title="Updated", body=None, labels=["bug"], state=None
    )
    assert result["number"] == 8


def test_update_issue_state_only():
    mod = _load_skill()
    mod.run(action="update_issue", repo="owner/repo", number=8, state="closed")
    mod.sdk["github"].update_issue.assert_called_once_with(
        "owner/repo", 8, title=None, body=None, labels=None, state="closed"
    )


def test_create_label():
    mod = _load_skill()
    result = mod.run(
        action="create_label", repo="owner/repo", name="triage", color="ff0000", description="d"
    )
    mod.sdk["github"].create_label.assert_called_once_with("owner/repo", "triage", "ff0000", "d")
    assert result["name"] == "triage"


def test_create_label_defaults():
    mod = _load_skill()
    mod.run(action="create_label", repo="owner/repo", name="triage")
    mod.sdk["github"].create_label.assert_called_once_with("owner/repo", "triage", "ededed", "")


def test_create_pr():
    mod = _load_skill()
    result = mod.run(action="create_pr", repo="owner/repo", title="My PR", body="body", head="feature")
    mod.sdk["github"].create_pr.assert_called_once_with("owner/repo", "My PR", "body", "feature", "main")
    assert result["number"] == 11


def test_get_pr():
    mod = _load_skill()
    result = mod.run(action="get_pr", repo="owner/repo", number=12)
    mod.sdk["github"].get_pr.assert_called_once_with("owner/repo", 12)
    assert result["number"] == 12


def test_get_pr_diff():
    mod = _load_skill()
    result = mod.run(action="get_pr_diff", repo="owner/repo", number=12)
    mod.sdk["github"].get_pr_diff.assert_called_once_with("owner/repo", 12)
    assert result[0]["filename"] == "a.py"


def test_merge_pr_defaults():
    mod = _load_skill()
    result = mod.run(action="merge_pr", repo="owner/repo", number=12)
    mod.sdk["github"].merge_pr.assert_called_once_with(
        "owner/repo", 12, merge_method="squash", commit_title=None, commit_message=None
    )
    assert result["merged"] is True


def test_merge_pr_explicit_commit_message():
    mod = _load_skill()
    mod.run(
        action="merge_pr",
        repo="owner/repo",
        number=12,
        commit_title="Squash: my PR",
        commit_message="Details here",
    )
    mod.sdk["github"].merge_pr.assert_called_once_with(
        "owner/repo", 12, merge_method="squash", commit_title="Squash: my PR", commit_message="Details here"
    )


def test_create_repo_private_by_default():
    mod = _load_skill()
    mod.sdk["github"].create_repo.return_value = {"full_name": "org/new-repo"}
    result = mod.run(action="create_repo", name="new-repo")
    mod.sdk["github"].create_repo.assert_called_once_with("new-repo", "", True)
    assert result["full_name"] == "org/new-repo"


def test_create_repo_explicit_public():
    mod = _load_skill()
    mod.sdk["github"].create_repo.return_value = {"full_name": "org/new-repo"}
    result = mod.run(action="create_repo", name="new-repo", description="d", private=False)
    mod.sdk["github"].create_repo.assert_called_once_with("new-repo", "d", False)
    assert result["full_name"] == "org/new-repo"


def test_unknown_action_returns_error():
    mod = _load_skill()
    result = mod.run(action="invalid_action", repo="owner/repo")
    assert "error" in result
    assert "invalid_action" in result["error"]
