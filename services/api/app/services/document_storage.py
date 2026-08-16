"""Short-lived raw document storage adapters for synthetic demo uploads."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol, cast
from uuid import UUID

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from services.api.app.config import Settings


@dataclass(frozen=True)
class UploadTarget:
    """A bounded upload destination returned to an authenticated client."""

    url: str
    headers: dict[str, str]
    expires_in_seconds: int


@dataclass(frozen=True)
class RawDocumentReference:
    """Non-sensitive durable reference stored with the document row."""

    bucket: str | None
    key: str | None


class RawDocumentStore(Protocol):
    """Narrow interface used by the deterministic ingestion workflow."""

    @property
    def label(self) -> str: ...

    def reference(self, document_id: UUID) -> RawDocumentReference: ...

    def upload_target(
        self,
        document_id: UUID,
        *,
        content_type: str,
        sha256_hex: str,
    ) -> UploadTarget: ...

    def accept_local(self, document_id: UUID, content: bytes) -> None: ...

    def read(self, document_id: UUID) -> bytes: ...

    def delete(self, document_id: UUID) -> None: ...


class FilesystemRawDocumentStore:
    """Atomic, temporary filesystem adapter retained for AWS-free local use."""

    def __init__(self, directory: Path, *, expires_in_seconds: int = 900) -> None:
        self._directory = directory
        self._directory.mkdir(parents=True, exist_ok=True)
        self._expires_in_seconds = expires_in_seconds

    @property
    def label(self) -> str:
        return "temporary-filesystem"

    def _path(self, document_id: UUID) -> Path:
        return self._directory / f"{document_id}.upload"

    def reference(self, document_id: UUID) -> RawDocumentReference:
        del document_id
        return RawDocumentReference(bucket=None, key=None)

    def upload_target(
        self,
        document_id: UUID,
        *,
        content_type: str,
        sha256_hex: str,
    ) -> UploadTarget:
        del sha256_hex
        return UploadTarget(
            url=f"/v1/local-uploads/{document_id}",
            headers={"Content-Type": content_type},
            expires_in_seconds=self._expires_in_seconds,
        )

    def accept_local(self, document_id: UUID, content: bytes) -> None:
        target = self._path(document_id)
        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(content)
        temporary.replace(target)

    def read(self, document_id: UUID) -> bytes:
        return self._path(document_id).read_bytes()

    def delete(self, document_id: UUID) -> None:
        self._path(document_id).unlink(missing_ok=True)


class S3Client(Protocol):
    """Small boto3 surface that keeps unit tests independent of AWS."""

    def generate_presigned_url(
        self,
        ClientMethod: str,
        Params: dict[str, Any],
        ExpiresIn: int,
        HttpMethod: str,
    ) -> str: ...

    def get_object(self, **kwargs: Any) -> dict[str, Any]: ...

    def delete_object(self, **kwargs: Any) -> dict[str, Any]: ...


class S3RawDocumentStore:
    """KMS-encrypted S3 adapter using short-lived SigV4 PUT URLs."""

    def __init__(
        self,
        client: S3Client,
        *,
        bucket: str,
        prefix: str,
        kms_key_arn: str = "",
        expires_in_seconds: int = 900,
    ) -> None:
        self._client = client
        self._bucket = bucket
        self._prefix = prefix.strip("/")
        self._kms_key_arn = kms_key_arn.strip()
        self._expires_in_seconds = expires_in_seconds

    @property
    def label(self) -> str:
        return "s3-kms"

    def _key(self, document_id: UUID) -> str:
        return f"{self._prefix}/{document_id}.upload"

    def reference(self, document_id: UUID) -> RawDocumentReference:
        return RawDocumentReference(bucket=self._bucket, key=self._key(document_id))

    def _encryption_parameters(self) -> dict[str, str]:
        parameters = {"ServerSideEncryption": "aws:kms"}
        if self._kms_key_arn:
            parameters["SSEKMSKeyId"] = self._kms_key_arn
        return parameters

    def upload_target(
        self,
        document_id: UUID,
        *,
        content_type: str,
        sha256_hex: str,
    ) -> UploadTarget:
        checksum = base64.b64encode(bytes.fromhex(sha256_hex)).decode("ascii")
        metadata = {
            "bonetwin-sha256": sha256_hex,
            "synthetic-only": "true",
        }
        parameters: dict[str, Any] = {
            "Bucket": self._bucket,
            "Key": self._key(document_id),
            "ContentType": content_type,
            "ChecksumSHA256": checksum,
            "Metadata": metadata,
            **self._encryption_parameters(),
        }
        try:
            url = self._client.generate_presigned_url(
                "put_object",
                Params=parameters,
                ExpiresIn=self._expires_in_seconds,
                HttpMethod="PUT",
            )
        except (BotoCoreError, ClientError) as error:
            raise ValueError("S3 upload authorization could not be created") from error

        headers = {
            "Content-Type": content_type,
            "x-amz-checksum-sha256": checksum,
            "x-amz-meta-bonetwin-sha256": sha256_hex,
            "x-amz-meta-synthetic-only": "true",
            "x-amz-server-side-encryption": "aws:kms",
        }
        if self._kms_key_arn:
            headers["x-amz-server-side-encryption-aws-kms-key-id"] = self._kms_key_arn
        return UploadTarget(
            url=url,
            headers=headers,
            expires_in_seconds=self._expires_in_seconds,
        )

    def accept_local(self, document_id: UUID, content: bytes) -> None:
        del document_id, content
        raise ValueError("S3 mode requires the provided direct upload URL")

    def read(self, document_id: UUID) -> bytes:
        try:
            response = self._client.get_object(
                Bucket=self._bucket,
                Key=self._key(document_id),
                ChecksumMode="ENABLED",
            )
            body = response.get("Body")
            if body is None or not callable(getattr(body, "read", None)):
                raise ValueError("S3 returned an invalid document body")
            content = cast(bytes, body.read())
        except (BotoCoreError, ClientError) as error:
            raise ValueError("uploaded S3 document is unavailable") from error

        returned_checksum = response.get("ChecksumSHA256")
        calculated_checksum = base64.b64encode(sha256(content).digest()).decode("ascii")
        if returned_checksum is not None and returned_checksum != calculated_checksum:
            raise ValueError("S3 object checksum validation failed")
        return content

    def delete(self, document_id: UUID) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=self._key(document_id))
        except (BotoCoreError, ClientError) as error:
            raise ValueError("S3 document cleanup failed") from error


def create_raw_document_store(
    settings: Settings,
    *,
    upload_directory: Path | None = None,
) -> RawDocumentStore:
    """Create the configured raw-document adapter without exposing credentials."""
    if settings.raw_document_store_mode == "filesystem":
        directory = upload_directory or (
            Path(__file__).resolve().parents[4] / "tmp" / "local-uploads"
        )
        return FilesystemRawDocumentStore(
            directory,
            expires_in_seconds=settings.s3_presigned_url_expiry_seconds,
        )

    session = boto3.Session(
        profile_name=settings.aws_profile or None,
        region_name=settings.aws_region,
    )
    client = cast(
        S3Client,
        session.client(
            "s3",
            config=Config(
                signature_version="s3v4",
                connect_timeout=5,
                read_timeout=30,
                retries={"max_attempts": 3, "mode": "standard"},
                s3={"addressing_style": "virtual"},
            ),
        ),
    )
    return S3RawDocumentStore(
        client,
        bucket=settings.s3_document_bucket,
        prefix=settings.s3_document_prefix,
        kms_key_arn=settings.kms_key_arn,
        expires_in_seconds=settings.s3_presigned_url_expiry_seconds,
    )
