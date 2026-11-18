"""
EyeSpeak AI - Middleware Configuration
Centralizes HTTP middleware setup including Cross-Origin Resource Sharing (CORS).
Allows all origins, all HTTP methods, and all headers cleanly.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def setup_cors_middleware(app: FastAPI) -> None:
    """
    Attaches and configures CORS middleware to allow all origins,
    methods, and headers for smooth cross-origin browser and mobile client access.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
