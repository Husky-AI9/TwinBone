from services.ingestion import DATA_POLICY


def test_ingestion_scaffold_is_synthetic_only() -> None:
    assert DATA_POLICY == "synthetic-only"
