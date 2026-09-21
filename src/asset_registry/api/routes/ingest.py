from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from asset_registry.errors import AppError
from asset_registry.auth.deps import require_admin
from asset_registry.db.models import User
from asset_registry.db.session import get_db
from asset_registry.ingest.pipeline import MissingColumnsError, StrictIngestAborted, ingest_csv_handle
from asset_registry.logging_setup import configure_logging
from asset_registry.schemas import IngestResponse

router = APIRouter(prefix="/ingest", tags=["Ingestion"])


@router.post(
    "/upload",
    response_model=IngestResponse,
    summary="Upload a day's CSV file (administrator only)",
)
def upload_csv(
    file: UploadFile = File(..., description="Handheld unit CSV export"),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    logger = configure_logging()
    ingest_log = __import__("logging").getLogger("asset_registry.ingest")
    try:
        # UploadFile.file is a SpooledTemporaryFile with a text wrapper needed for csv.
        text = file.file
        raw = text.read()
        if isinstance(raw, bytes):
            content = raw.decode("utf-8-sig")
        else:
            content = raw
    except UnicodeDecodeError as exc:
        raise AppError(
            status_code=422,
            error="validation_error",
            message="The uploaded file is not valid UTF-8 text.",
            details=[{"field": "file", "reason": str(exc)}],
        ) from exc

    from io import StringIO

    handle = StringIO(content)
    try:
        result = ingest_csv_handle(db, handle, source=file.filename or "upload")
    except MissingColumnsError as exc:
        raise AppError(
            status_code=422,
            error="validation_error",
            message=str(exc),
            details=[{"field": "file", "reason": f"missing columns: {', '.join(exc.missing)}"}],
        ) from exc
    except StrictIngestAborted as exc:
        db.rollback()
        raise AppError(
            status_code=422,
            error="validation_error",
            message="Strict ingest aborted.",
            details=[{"field": "file", "reason": exc.reason}],
        ) from exc

    ingest_log.info(
        "upload source=%s read=%s accepted=%s rejected=%s",
        file.filename,
        result.rows_read,
        result.rows_accepted,
        result.rows_rejected,
    )
    logger.info("network ingest complete")
    return {
        "rows_read": result.rows_read,
        "rows_accepted": result.rows_accepted,
        "rows_rejected": result.rows_rejected,
        "rejects": result.rejects,
    }
