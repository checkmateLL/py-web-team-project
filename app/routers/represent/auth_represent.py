from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pathlib import Path

router = APIRouter(prefix="/auth")

templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent.parent / "templates")
)


@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    """
    rendering html page login_form.html
    """
    message = None
    error_message = None
    return templates.TemplateResponse(
        "login_form.html",
        {
            "request": request,
            "message": message,
            "error_message": error_message
        },
    )


@router.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    """
    rendering html page login_form.html
    """
    return templates.TemplateResponse(
        "register_form.html", {"request": request, "error_message": None}
    )
