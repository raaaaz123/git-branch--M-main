"""
Upload Router for handling file uploads to R2 storage
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import Optional
from app.services.r2_service import r2_service

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    workspace_id: Optional[str] = Form(None),
    agent_id: Optional[str] = Form(None)
):
    """
    Upload an image file to R2 storage

    Accepts: JPG, PNG, SVG (max 1MB)
    Returns: file_url, file_key
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/svg+xml"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: JPG, PNG, SVG"
        )

    # Read file content
    file_content = await file.read()

    # Validate file size (1MB = 1,048,576 bytes)
    max_size = 1 * 1024 * 1024  # 1MB
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds 1MB limit"
        )

    # Upload to R2
    result = r2_service.upload_file(
        file_content=file_content,
        filename=file.filename or "image",
        content_type=file.content_type or "image/jpeg",
        workspace_id=workspace_id,
        agent_id=agent_id
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to upload file")
        )

    return {
        "success": True,
        "file_url": result["file_url"],
        "file_key": result["file_key"],
        "original_filename": result["original_filename"]
    }
