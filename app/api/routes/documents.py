from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DatabaseSession, Tenant, require_roles
from app.core.config import Settings, get_settings
from app.models.document import Document
from app.models.organization import MembershipRole
from app.schemas.document import DocumentResponse
from app.services.audit import record_audit_event
from app.services.storage import (
    DocumentTooLargeError,
    resolve_storage_key,
    safe_file_name,
    store_upload,
)

router = APIRouter()
write_roles = require_roles(MembershipRole.OWNER, MembershipRole.ADMIN, MembershipRole.MANAGER)


async def find_document(session: DatabaseSession, tenant: Tenant, document_id: UUID) -> Document:
    document = await session.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.organization_id == tenant.organization_id,
        )
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[write_roles],
)
async def upload_document(
    session: DatabaseSession,
    tenant: Tenant,
    user: CurrentUser,
    settings: Annotated[Settings, Depends(get_settings)],
    file: Annotated[UploadFile, File()],
    resource_type: Annotated[str, Form(min_length=1, max_length=80)],
    resource_id: Annotated[UUID, Form()],
) -> Document:
    document_id = uuid4()
    storage_root = Path(settings.storage_root)
    try:
        storage_key, size_bytes, checksum = await store_upload(
            file,
            root=storage_root,
            organization_id=tenant.organization_id,
            document_id=document_id,
            max_bytes=settings.max_document_size_bytes,
        )
    except DocumentTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    document = Document(
        id=document_id,
        organization_id=tenant.organization_id,
        file_name=safe_file_name(file.filename or "document"),
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size_bytes,
        checksum_sha256=checksum,
        storage_key=storage_key,
        resource_type=resource_type.strip(),
        resource_id=resource_id,
        uploaded_by_id=user.id,
    )
    session.add(document)
    record_audit_event(
        session,
        organization_id=tenant.organization_id,
        actor_user_id=user.id,
        action="document.uploaded",
        resource_type="document",
        resource_id=document.id,
        details={"file_name": document.file_name, "size_bytes": size_bytes},
    )
    try:
        await session.commit()
    except Exception:
        resolve_storage_key(storage_root, storage_key).unlink(missing_ok=True)
        raise
    return document


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    session: DatabaseSession,
    tenant: Tenant,
    resource_type: str | None = Query(default=None, max_length=80),
    resource_id: UUID | None = None,
) -> list[Document]:
    query = select(Document).where(Document.organization_id == tenant.organization_id)
    if resource_type is not None:
        query = query.where(Document.resource_type == resource_type)
    if resource_id is not None:
        query = query.where(Document.resource_id == resource_id)
    result = await session.scalars(query.order_by(Document.created_at.desc()))
    return list(result.all())


@router.get("/{document_id}/content", response_class=FileResponse)
async def download_document(
    document_id: UUID,
    session: DatabaseSession,
    tenant: Tenant,
    settings: Annotated[Settings, Depends(get_settings)],
) -> FileResponse:
    document = await find_document(session, tenant, document_id)
    path = resolve_storage_key(Path(settings.storage_root), document.storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Document content is unavailable")
    return FileResponse(path, media_type=document.content_type, filename=document.file_name)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[write_roles],
)
async def delete_document(
    document_id: UUID,
    session: DatabaseSession,
    tenant: Tenant,
    user: CurrentUser,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    document = await find_document(session, tenant, document_id)
    path = resolve_storage_key(Path(settings.storage_root), document.storage_key)
    record_audit_event(
        session,
        organization_id=tenant.organization_id,
        actor_user_id=user.id,
        action="document.deleted",
        resource_type="document",
        resource_id=document.id,
    )
    await session.delete(document)
    await session.commit()
    path.unlink(missing_ok=True)
