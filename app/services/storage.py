import hashlib
import re
from pathlib import Path
from uuid import UUID

import aiofiles
from fastapi import UploadFile


class DocumentTooLargeError(ValueError):
    pass


def safe_file_name(file_name: str) -> str:
    name = Path(file_name).name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-")
    return cleaned[:180] or "document"


async def store_upload(
    upload: UploadFile,
    *,
    root: Path,
    organization_id: UUID,
    document_id: UUID,
    max_bytes: int,
) -> tuple[str, int, str]:
    file_name = safe_file_name(upload.filename or "document")
    storage_key = f"{organization_id}/{document_id}/{file_name}"
    destination = root / storage_key
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".uploading")
    digest = hashlib.sha256()
    size = 0
    try:
        async with aiofiles.open(temporary, "wb") as stored:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise DocumentTooLargeError(f"Document exceeds {max_bytes} bytes")
                digest.update(chunk)
                await stored.write(chunk)
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()
    return storage_key, size, digest.hexdigest()


def resolve_storage_key(root: Path, storage_key: str) -> Path:
    root = root.resolve()
    candidate = (root / storage_key).resolve()
    if root not in candidate.parents:
        raise ValueError("Invalid storage key")
    return candidate
