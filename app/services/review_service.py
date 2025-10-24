"""
Review form service for managing review forms and submissions
"""
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from app.models import (
    ReviewForm, ReviewSubmission, CreateReviewFormRequest, 
    SubmitReviewRequest, ReviewField, ReviewFormSettings
)


class ReviewService:
    def __init__(self):
        # In-memory storage for demo (replace with database in production)
        self.review_forms_db: Dict[str, ReviewForm] = {}
        self.review_submissions_db: Dict[str, List[ReviewSubmission]] = {}

    def create_review_form(self, request: CreateReviewFormRequest) -> Dict[str, Any]:
        """Create a new review form"""
        try:
            form_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            form = ReviewForm(
                id=form_id,
                businessId=request.businessId,
                title=request.title,
                description=request.description,
                isActive=True,
                createdAt=now,
                updatedAt=now,
                fields=request.fields,
                settings=request.settings
            )
            
            self.review_forms_db[form_id] = form
            
            return {
                "success": True,
                "data": form.dict()
            }
        except Exception as e:
            raise Exception(str(e))

    def get_business_review_forms(self, business_id: str) -> Dict[str, Any]:
        """Get all review forms for a business"""
        try:
            forms = [form for form in self.review_forms_db.values() if form.businessId == business_id]
            return {
                "success": True,
                "data": [form.dict() for form in forms]
            }
        except Exception as e:
            raise Exception(str(e))

    def get_review_form(self, form_id: str) -> Dict[str, Any]:
        """Get a specific review form"""
        try:
            if form_id not in self.review_forms_db:
                raise Exception("Review form not found")
            
            form = self.review_forms_db[form_id]
            return {
                "success": True,
                "data": form.dict()
            }
        except Exception as e:
            raise Exception(str(e))

    def submit_review_form(self, form_id: str, request: SubmitReviewRequest) -> Dict[str, Any]:
        """Submit a review form"""
        try:
            if form_id not in self.review_forms_db:
                raise Exception("Review form not found")
            
            form = self.review_forms_db[form_id]
            if not form.isActive:
                raise Exception("Review form is not active")
            
            submission_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            # Prepare user info with location and device data
            user_info = request.userInfo or {}
            if request.deviceInfo:
                user_info["device"] = request.deviceInfo
            
            # Add location data if enabled
            if form.settings.collectLocation:
                user_info["location"] = {
                    "country": "Unknown",
                    "region": "Unknown", 
                    "city": "Unknown"
                }
            
            submission = ReviewSubmission(
                id=submission_id,
                formId=form_id,
                businessId=form.businessId,
                submittedAt=now,
                userInfo=user_info,
                responses=request.responses,
                isAnonymous=not user_info.get("email") and not user_info.get("name")
            )
            
            if form_id not in self.review_submissions_db:
                self.review_submissions_db[form_id] = []
            
            self.review_submissions_db[form_id].append(submission)
            
            return {
                "success": True,
                "data": {"submissionId": submission_id}
            }
        except Exception as e:
            raise Exception(str(e))

    def get_review_form_submissions(self, form_id: str) -> Dict[str, Any]:
        """Get submissions for a review form"""
        try:
            if form_id not in self.review_forms_db:
                raise Exception("Review form not found")
            
            submissions = self.review_submissions_db.get(form_id, [])
            return {
                "success": True,
                "data": [submission.dict() for submission in submissions]
            }
        except Exception as e:
            raise Exception(str(e))

    def get_review_form_analytics(self, form_id: str) -> Dict[str, Any]:
        """Get analytics for a review form"""
        try:
            if form_id not in self.review_forms_db:
                raise Exception("Review form not found")
            
            form = self.review_forms_db[form_id]
            submissions = self.review_submissions_db.get(form_id, [])
            
            # Calculate analytics
            total_submissions = len(submissions)
            completion_rate = 100.0 if total_submissions > 0 else 0.0
            
            # Calculate average rating
            average_rating = 0.0
            rating_responses = []
            for submission in submissions:
                for response in submission.responses:
                    if response.fieldType == "rating" and isinstance(response.value, (int, float)):
                        rating_responses.append(response.value)
            
            if rating_responses:
                average_rating = sum(rating_responses) / len(rating_responses)
            
            # Field analytics
            field_analytics = []
            for field in form.fields:
                field_responses = []
                for submission in submissions:
                    for response in submission.responses:
                        if response.fieldId == field.id:
                            field_responses.append(response.value)
                
                field_analytics.append({
                    "fieldId": field.id,
                    "fieldLabel": field.label,
                    "fieldType": field.type,
                    "responseCount": len(field_responses),
                    "averageValue": sum(field_responses) / len(field_responses) if field_responses and field.type == "rating" else None,
                    "commonResponses": []
                })
            
            # Location stats
            location_stats = []
            country_counts = {}
            for submission in submissions:
                country = submission.userInfo.get("location", {}).get("country", "Unknown")
                country_counts[country] = country_counts.get(country, 0) + 1
            
            for country, count in country_counts.items():
                location_stats.append({
                    "country": country,
                    "count": count
                })
            
            # Device stats
            device_stats = []
            platform_counts = {}
            for submission in submissions:
                platform = submission.userInfo.get("device", {}).get("platform", "Unknown")
                browser = submission.userInfo.get("device", {}).get("browser", "Unknown")
                key = f"{platform} - {browser}"
                platform_counts[key] = platform_counts.get(key, 0) + 1
            
            for platform, count in platform_counts.items():
                parts = platform.split(" - ")
                device_stats.append({
                    "platform": parts[0],
                    "browser": parts[1] if len(parts) > 1 else "Unknown",
                    "count": count
                })
            
            analytics = {
                "totalSubmissions": total_submissions,
                "completionRate": completion_rate,
                "averageRating": average_rating,
                "fieldAnalytics": field_analytics,
                "locationStats": location_stats,
                "deviceStats": device_stats,
                "timeStats": []
            }
            
            return {
                "success": True,
                "data": analytics
            }
        except Exception as e:
            raise Exception(str(e))

    def update_review_form(self, form_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a review form"""
        try:
            if form_id not in self.review_forms_db:
                raise Exception("Review form not found")
            
            form = self.review_forms_db[form_id]
            updates["updatedAt"] = datetime.now().isoformat()
            
            for key, value in updates.items():
                if hasattr(form, key):
                    setattr(form, key, value)
            
            self.review_forms_db[form_id] = form
            
            return {
                "success": True,
                "data": form.dict()
            }
        except Exception as e:
            raise Exception(str(e))

    def delete_review_form(self, form_id: str) -> Dict[str, Any]:
        """Delete a review form"""
        try:
            if form_id not in self.review_forms_db:
                raise Exception("Review form not found")
            
            del self.review_forms_db[form_id]
            if form_id in self.review_submissions_db:
                del self.review_submissions_db[form_id]
            
            return {
                "success": True,
                "data": None
            }
        except Exception as e:
            raise Exception(str(e))


# Global service instance
review_service = ReviewService()
