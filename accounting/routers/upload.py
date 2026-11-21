import hmac
import os

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile

from accounting.utils.etl import process_cashew_upload

router = APIRouter(prefix="/accounting")


def _verify_token(header_token, form_token):
    """Authenticate upload via `X-Upload-Token` header or `token` form field against `CASHEW_UPLOAD_TOKEN`."""
    expected = os.environ.get("CASHEW_UPLOAD_TOKEN", "")
    if not expected:
        raise HTTPException(
            status_code=500, detail="CASHEW_UPLOAD_TOKEN is not configured"
        )
    provided = header_token or form_token or ""
    # Constant-time comparison prevents timing side-channel leaks
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Invalid upload token")


@router.post("/upload", summary="Upload and process a Cashew .sql backup")
async def upload_cashew(
    file: UploadFile = File(...),
    token: str = Form(default=None),
    x_upload_token: str = Header(default=None),
):
    """Validate, enrich with daily FX rates, and atomically activate a Cashew SQLite export."""
    _verify_token(x_upload_token, token)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    try:
        return process_cashew_upload(content, file.filename)
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
