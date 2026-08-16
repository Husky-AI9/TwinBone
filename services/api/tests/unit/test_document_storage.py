from __future__ import annotations

import base64
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID

from services.api.app.services.document_storage import (
    FilesystemRawDocumentStore,
    S3RawDocumentStore,
)

DOCUMENT_ID = UUID("40000000-0000-4000-8000-000000000099")
CONTENT = b"%PDF-synthetic-storage-test"
DIGEST = sha256(CONTENT).hexdigest()


class FakeBody:
    def __init__(self, content: bytes) -> None:
        self._content = content

    def read(self) -> bytes:
        return self._content


class FakeS3Client:
    def __init__(self) -> None:
        self.presign: dict[str, Any] | None = None
        self.get: dict[str, Any] | None = None
        self.deleted: dict[str, Any] | None = None

    def generate_presigned_url(
        self,
        ClientMethod: str,
        Params: dict[str, Any],
        ExpiresIn: int,
        HttpMethod: str,
    ) -> str:
        self.presign = {
            "method": ClientMethod,
            "params": Params,
            "expires": ExpiresIn,
            "http_method": HttpMethod,
        }
        return "https://synthetic-bucket.s3.us-west-2.amazonaws.com/signed-object?signature=test"

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        self.get = kwargs
        return {
            "Body": FakeBody(CONTENT),
            "ChecksumSHA256": base64.b64encode(sha256(CONTENT).digest()).decode("ascii"),
        }

    def delete_object(self, **kwargs: Any) -> dict[str, Any]:
        self.deleted = kwargs
        return {}


def test_filesystem_store_round_trip_and_cleanup(tmp_path: Path) -> None:
    store = FilesystemRawDocumentStore(tmp_path)
    target = store.upload_target(
        DOCUMENT_ID,
        content_type="application/pdf",
        sha256_hex=DIGEST,
    )

    assert target.url == f"/v1/local-uploads/{DOCUMENT_ID}"
    assert target.headers == {"Content-Type": "application/pdf"}
    store.accept_local(DOCUMENT_ID, CONTENT)
    assert store.read(DOCUMENT_ID) == CONTENT
    store.delete(DOCUMENT_ID)
    assert list(tmp_path.iterdir()) == []


def test_s3_store_signs_checksum_metadata_and_kms_headers() -> None:
    client = FakeS3Client()
    store = S3RawDocumentStore(
        client,
        bucket="synthetic-bucket",
        prefix="bonetwin/raw-local",
        kms_key_arn="arn:aws:kms:us-west-2:111122223333:key/synthetic-test",
    )

    target = store.upload_target(
        DOCUMENT_ID,
        content_type="application/pdf",
        sha256_hex=DIGEST,
    )

    assert target.url.startswith("https://synthetic-bucket.s3.us-west-2.amazonaws.com/")
    assert client.presign is not None
    parameters = client.presign["params"]
    assert parameters["Bucket"] == "synthetic-bucket"
    assert parameters["Key"] == f"bonetwin/raw-local/{DOCUMENT_ID}.upload"
    assert parameters["ChecksumSHA256"] == target.headers["x-amz-checksum-sha256"]
    assert parameters["Metadata"] == {
        "bonetwin-sha256": DIGEST,
        "synthetic-only": "true",
    }
    assert parameters["ServerSideEncryption"] == "aws:kms"
    assert target.headers["x-amz-server-side-encryption"] == "aws:kms"
    assert "selected.pdf" not in parameters["Key"]


def test_s3_store_reads_with_checksum_validation_and_deletes() -> None:
    client = FakeS3Client()
    store = S3RawDocumentStore(
        client,
        bucket="synthetic-bucket",
        prefix="bonetwin/raw-local",
    )

    assert store.read(DOCUMENT_ID) == CONTENT
    assert client.get == {
        "Bucket": "synthetic-bucket",
        "Key": f"bonetwin/raw-local/{DOCUMENT_ID}.upload",
        "ChecksumMode": "ENABLED",
    }
    store.delete(DOCUMENT_ID)
    assert client.deleted == {
        "Bucket": "synthetic-bucket",
        "Key": f"bonetwin/raw-local/{DOCUMENT_ID}.upload",
    }
