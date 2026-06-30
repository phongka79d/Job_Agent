import json
from pathlib import Path

from fastapi.testclient import TestClient

from app import main as app_main
from app.api import schemas as api_schemas
from app.core import constants
from app.services import job_processing_service, qdrant_service
from scripts import export_api_contract


def _patch_startup_dependencies(monkeypatch):
    calls: list[str] = []

    async def fake_init_db() -> None:
        calls.append("init_db")

    async def fake_ensure_collection() -> None:
        calls.append("ensure_collection")

    monkeypatch.setattr(app_main, "init_db", fake_init_db)
    monkeypatch.setattr(app_main, "ensure_collection", fake_ensure_collection)
    return calls


def test_export_script_matches_checked_in_contract(tmp_path, monkeypatch):
    checked_in_contract_path = export_api_contract.REPOSITORY_ROOT / "shared" / "api-contract.json"
    assert checked_in_contract_path.exists()

    generated_contract_path = tmp_path / "api-contract.json"
    monkeypatch.setattr(export_api_contract, "CONTRACT_PATH", generated_contract_path)

    assert export_api_contract.write_api_contract() == generated_contract_path
    assert generated_contract_path.read_text(encoding="utf-8") == checked_in_contract_path.read_text(
        encoding="utf-8"
    )


def test_contract_content_comes_from_backend_owners():
    contract = export_api_contract.build_api_contract()

    assert contract["job_statuses"] == list(constants.JOB_STATUSES)
    assert contract["tracked_job_statuses"] == list(constants.TRACKED_JOB_STATUSES)
    assert contract["application_statuses"] == list(constants.APPLICATION_STATUSES)
    assert contract["jd_statuses"] == list(constants.JD_STATUSES)
    assert contract["parse_statuses"] == list(constants.PARSE_STATUSES)
    assert contract["extraction_statuses"] == list(constants.EXTRACTION_STATUSES)
    assert contract["source_platforms"] == list(constants.SOURCE_PLATFORMS)
    assert contract["input_sources"] == list(constants.INPUT_SOURCES)

    expected_transitions = {
        status: [
            target
            for target in constants.JOB_STATUSES
            if target in job_processing_service.ALLOWED_STATUS_TRANSITIONS[status]
        ]
        for status in constants.JOB_STATUSES
    }
    assert contract["allowed_status_transitions"] == expected_transitions
    assert export_api_contract.ALLOWED_STATUS_TRANSITIONS is (
        job_processing_service.ALLOWED_STATUS_TRANSITIONS
    )

    assert contract["endpoints"] == export_api_contract.ENDPOINTS
    assert contract["endpoints"]["loadMockJobs"] == {
        "method": "POST",
        "path": "/api/jobs/mock-load",
        "request_schema": "MockLoadRequest",
        "response_schema": "IngestionResponse",
    }
    assert contract["endpoints"]["getBatchSummary"] == {
        "method": "GET",
        "path": "/api/batches/{batch_id}/summary",
        "response_schema": "BatchSummaryResponse",
    }

    schemas = contract["schemas"]
    for model in export_api_contract.SCHEMA_MODELS:
        assert schemas[model.__name__] == model.model_json_schema()
    assert schemas["JobResponse"] == api_schemas.JobResponse.model_json_schema()
    assert schemas["IngestionResponse"] == api_schemas.IngestionResponse.model_json_schema()
    assert schemas["BatchSummaryResponse"] == api_schemas.BatchSummaryResponse.model_json_schema()


def test_contract_builder_reads_mutable_backend_owner_values(monkeypatch):
    monkeypatch.setattr(constants, "SOURCE_PLATFORMS", ("unit_test_source",))
    monkeypatch.setattr(
        export_api_contract,
        "ALLOWED_STATUS_TRANSITIONS",
        {status: frozenset() for status in constants.JOB_STATUSES},
    )

    contract = export_api_contract.build_api_contract()

    assert contract["source_platforms"] == ["unit_test_source"]
    assert contract["allowed_status_transitions"] == {
        status: [] for status in constants.JOB_STATUSES
    }


def test_cors_allows_local_react_dev_origin(monkeypatch):
    _patch_startup_dependencies(monkeypatch)

    with TestClient(app_main.app) as client:
        response = client.options(
            "/api/jobs/search",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        disallowed_response = client.options(
            "/api/jobs/search",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert response.headers.get("access-control-allow-credentials") != "true"
    assert "access-control-allow-origin" not in disallowed_response.headers


def test_startup_delegates_qdrant_initialization_to_service_owner(monkeypatch):
    assert app_main.ensure_collection is qdrant_service.ensure_collection
    calls = _patch_startup_dependencies(monkeypatch)

    with TestClient(app_main.app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert calls == ["init_db", "ensure_collection"]

    main_source = Path(app_main.__file__).read_text(encoding="utf-8")
    assert "AsyncQdrantClient" not in main_source
    assert "QdrantService(" not in main_source
    assert "create_collection(" not in main_source
    assert "create_payload_index(" not in main_source
