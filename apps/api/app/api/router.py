"""Aggregated API router for version 1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, chat, files, groups, notes, projects, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(groups.router)
api_router.include_router(chat.router)
api_router.include_router(notes.router)
api_router.include_router(files.router)
api_router.include_router(projects.router)
