from services.workspace_store import WorkspaceStore


def test_workspace_store_save_and_search(tmp_path):
    store = WorkspaceStore(tmp_path / "workspace.sqlite3")
    document_id = store.save_document(
        title="Lab Report",
        collection_name="Health",
        text="Patient has diabetes and follow-up on March 20, 2025.",
        domain="medical",
        subtype="lab_report",
        analysis={"entity_count": 2, "action_items": [{"title": "Track date"}]},
    )
    assert document_id
    results = store.search("diabetes")
    assert results
    detail = store.get_document(document_id)
    assert detail is not None
    assert detail["title"] == "Lab Report"

