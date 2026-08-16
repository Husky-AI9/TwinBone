import math

from pytest import raises

from services.api.app.db.vector import EMBEDDING_DIMENSIONS, vector_literal


def test_vector_literal_requires_exact_dimension_and_finite_values() -> None:
    values = [0.0] * EMBEDDING_DIMENSIONS
    values[0] = 1.0
    rendered = vector_literal(values)
    assert rendered.startswith("[1,0,0")
    assert rendered.endswith("]")

    with raises(ValueError, match="exactly"):
        vector_literal([0.0])

    values[-1] = math.inf
    with raises(ValueError, match="finite"):
        vector_literal(values)
