from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from accounting.config import HTML_PATH

router = APIRouter(prefix="/accounting")


@router.get("", response_class=HTMLResponse, summary="Cashew upload webpage")
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def upload_page():
    """Serve the Cashew SQLite upload form HTML."""
    return HTMLResponse(content=HTML_PATH.read_text(encoding="utf-8"))
