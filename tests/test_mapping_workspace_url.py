"""Tests for clerk mapping workspace URL helpers."""

from utils.session_workflow import mapping_workspace_url, normalize_mapping_session_id


def test_normalize_mapping_session_id_rejects_sentinels():
    assert normalize_mapping_session_id(None) is None
    assert normalize_mapping_session_id("") is None
    assert normalize_mapping_session_id("None") is None
    assert normalize_mapping_session_id("null") is None
    assert normalize_mapping_session_id("abc-123") == "abc-123"


def test_mapping_workspace_url_includes_session():
    assert mapping_workspace_url("sess-1") == "/mapping?session_id=sess-1"
    assert mapping_workspace_url(None) == "/mapping"


def test_mapping_revision_workspace_url():
    from utils.session_workflow import mapping_revision_workspace_url

    assert mapping_revision_workspace_url("sess-1") == "/mapping?session_id=sess-1&revision=1"
