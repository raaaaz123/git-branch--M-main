"""
Review form router for managing review forms and submissions
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.models import (
    CreateReviewFormRequest, SubmitReviewRequest
)
from app.services.review_service import review_service

router = APIRouter(prefix="/api/review-forms", tags=["review-forms"])


@router.post("/", response_model=Dict[str, Any])
async def create_review_form(request: CreateReviewFormRequest):
    """Create a new review form"""
    try:
        result = review_service.create_review_form(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/business/{business_id}", response_model=Dict[str, Any])
async def get_business_review_forms(business_id: str):
    """Get all review forms for a business"""
    try:
        result = review_service.get_business_review_forms(business_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{form_id}", response_model=Dict[str, Any])
async def get_review_form(form_id: str):
    """Get a specific review form"""
    try:
        result = review_service.get_review_form(form_id)
        return result
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{form_id}/submit", response_model=Dict[str, Any])
async def submit_review_form(form_id: str, request: SubmitReviewRequest):
    """Submit a review form"""
    try:
        result = review_service.submit_review_form(form_id, request)
        return result
    except Exception as e:
        if "not found" in str(e).lower() or "not active" in str(e).lower():
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{form_id}/submissions", response_model=Dict[str, Any])
async def get_review_form_submissions(form_id: str):
    """Get submissions for a review form"""
    try:
        result = review_service.get_review_form_submissions(form_id)
        return result
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{form_id}/analytics", response_model=Dict[str, Any])
async def get_review_form_analytics(form_id: str):
    """Get analytics for a review form"""
    try:
        result = review_service.get_review_form_analytics(form_id)
        return result
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{form_id}", response_model=Dict[str, Any])
async def update_review_form(form_id: str, updates: Dict[str, Any]):
    """Update a review form"""
    try:
        result = review_service.update_review_form(form_id, updates)
        return result
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{form_id}", response_model=Dict[str, Any])
async def delete_review_form(form_id: str):
    """Delete a review form"""
    try:
        result = review_service.delete_review_form(form_id)
        return result
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))
