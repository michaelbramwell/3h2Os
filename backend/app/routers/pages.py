from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.core.auth import allow_anonymous

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
@allow_anonymous
async def read_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

