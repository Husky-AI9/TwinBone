from services.api.app import PRODUCT_NAME, SAFETY_BOUNDARY


def test_api_scaffold_preserves_safety_boundary() -> None:
    assert PRODUCT_NAME == "BoneTwin"
    assert "review preparation" in SAFETY_BOUNDARY
