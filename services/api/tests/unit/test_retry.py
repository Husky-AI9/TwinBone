from services.api.app.db.retry import (
    SERIALIZATION_FAILURE_SQLSTATE,
    retry_delay,
    sqlstate_for_exception,
)


class RetryableDriverError(Exception):
    sqlstate = SERIALIZATION_FAILURE_SQLSTATE


def test_retry_helpers_recognize_sqlstate_and_bound_jitter() -> None:
    assert sqlstate_for_exception(RetryableDriverError()) == "40001"
    assert (
        retry_delay(
            3,
            base_delay_seconds=0.1,
            max_delay_seconds=0.5,
            random_value=1.0,
        )
        == 0.5
    )
    assert (
        retry_delay(
            0,
            base_delay_seconds=0.1,
            max_delay_seconds=0.5,
            random_value=0.25,
        )
        == 0.025
    )
