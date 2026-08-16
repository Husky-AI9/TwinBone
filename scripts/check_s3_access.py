"""Exercise BoneTwin's browser-equivalent S3 upload, read, and cleanup path."""

from __future__ import annotations

from hashlib import sha256
from uuid import uuid4

import httpx

from services.api.app.config import get_settings
from services.api.app.services.document_storage import create_raw_document_store


def main() -> int:
    settings = get_settings()
    if settings.raw_document_store_mode != "s3":
        raise RuntimeError("Set RAW_DOCUMENT_STORE_MODE=s3 before checking S3 access")

    store = create_raw_document_store(settings)
    document_id = uuid4()
    content = b"%PDF-1.4\nBoneTwin synthetic S3 readiness probe only.\n%%EOF\n"
    target = store.upload_target(
        document_id,
        content_type="application/pdf",
        sha256_hex=sha256(content).hexdigest(),
    )
    uploaded = False
    try:
        response = httpx.put(
            target.url,
            headers=target.headers,
            content=content,
            timeout=30,
        )
        if response.status_code not in {200, 201, 204}:
            raise RuntimeError(f"S3 presigned PUT failed with HTTP {response.status_code}")
        uploaded = True
        if store.read(document_id) != content:
            raise RuntimeError("S3 readiness object did not round-trip exactly")
    finally:
        if uploaded:
            store.delete(document_id)

    print(
        "S3 SigV4 upload, checksum verification, KMS encryption request, read, and cleanup passed."
    )
    print("The readiness object was synthetic and has been deleted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
