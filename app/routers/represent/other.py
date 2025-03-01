from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pathlib import Path

router = APIRouter(prefix='/other')

templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))

@router.get('/contacts', response_class=HTMLResponse)
async def contacts_form(request:Request):
    """
    rendering html page login_form.html
    """
    return templates.TemplateResponse(
        'contacts.html',
        {
            'request':request, 
            'error_message':None
        }
    )

@router.get('/dashboard', response_class=HTMLResponse)
async def get_dushboard(request:Request):
    """
    rendering html page login_form.html
    """
    return templates.TemplateResponse(
        'dashboard.html',
        {
            'request':request, 
            'error_message':None
        }
    )

