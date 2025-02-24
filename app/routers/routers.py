from fastapi import APIRouter

from app.routers import auth, images, comments, admin_panel, search

api_router = APIRouter(prefix='/app')

api_router.include_router(
    auth.router,
    prefix='',
    tags=['auth'])

api_router.include_router(
    images.router,
    prefix='',
    tags=['images'])

api_router.include_router(
    comments.router,
    tags=['comments'])

api_router.include_router(
    admin_panel.router,
    tags=['admin-panel']
)

api_router.include_router(
    search.router,
    tags=['search']
)

