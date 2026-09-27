"""Aggregates all v1 route modules into a single router."""

from fastapi import APIRouter

from app.api.v1.routes import admin, auth, comments, exports, health, posts, tags, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(posts.router)
api_router.include_router(comments.router)
api_router.include_router(tags.router)
api_router.include_router(exports.router)
api_router.include_router(admin.router)
