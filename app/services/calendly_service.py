"""
Calendly API service for handling OAuth and event type operations
"""
import os
import httpx
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode


class CalendlyService:
    """Service for interacting with Calendly API"""
    
    def __init__(self):
        self.client_id = os.getenv("CALENDLY_CLIENT_ID")
        self.client_secret = os.getenv("CALENDLY_CLIENT_SECRET")
        self.redirect_uri = os.getenv("CALENDLY_REDIRECT_URI")
        self.base_url = "https://api.calendly.com"
        
    def get_oauth_url(self, state: str = None) -> str:
        """Generate OAuth authorization URL"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"🔗 Generating Calendly OAuth URL")
            logger.info(f"   Client ID: {self.client_id[:10] if self.client_id else 'None'}...")
            logger.info(f"   Redirect URI: {self.redirect_uri}")
            logger.info(f"   State: {state}")
            
            if not self.client_id:
                raise ValueError("CALENDLY_CLIENT_ID is not set in environment variables")
            if not self.redirect_uri:
                raise ValueError("CALENDLY_REDIRECT_URI is not set in environment variables")
            
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": "default"
        }
        
        if state:
            params["state"] = state
            
            oauth_url = f"https://auth.calendly.com/oauth/authorize?{urlencode(params)}"
            logger.info(f"✅ OAuth URL generated: {oauth_url[:100]}...")
            return oauth_url
            
        except Exception as e:
            logger.error(f"❌ Error generating OAuth URL: {str(e)}")
            logger.exception(e)
            raise
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://auth.calendly.com/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to exchange code for token: {response.text}")
                
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get current user information"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/users/me",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get user info: {response.text}")
                
            return response.json()
    
    async def get_event_types(self, access_token: str, user_uri: str) -> List[Dict[str, Any]]:
        """Get user's event types"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/event_types",
                params={"user": user_uri},
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get event types: {response.text}")
                
            data = response.json()
            return data.get("collection", [])
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://auth.calendly.com/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to refresh token: {response.text}")
                
            return response.json()
    
    async def revoke_token(self, token: str) -> bool:
        """Revoke access token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://auth.calendly.com/oauth/revoke",
                data={
                    "token": token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )
            
            return response.status_code == 200
    
    async def get_available_slots(self, access_token: str, event_type_uri: str, start_time: str = None, end_time: str = None) -> List[Dict[str, Any]]:
        """Get available time slots for an event type"""
        import logging
        from datetime import datetime, timedelta, timezone
        logger = logging.getLogger(__name__)
        
        try:
            # Calendly API constraints:
            # - Date range can be no greater than 1 week (7 days)
            # - start_time must be in the future
            # - Times must be in UTC and ISO 8601 format
            
            now = datetime.now(timezone.utc)
            
            # Ensure start_time is at least 1 minute in the future
            if not start_time:
                start_time = (now + timedelta(minutes=1)).isoformat().replace('+00:00', 'Z')
            else:
                # Parse and ensure it's in the future
                try:
                    parsed_start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    if parsed_start <= now:
                        start_time = (now + timedelta(minutes=1)).isoformat().replace('+00:00', 'Z')
                except:
                    start_time = (now + timedelta(minutes=1)).isoformat().replace('+00:00', 'Z')
            
            # Ensure end_time is within 7 days of start_time
            if not end_time:
                # Parse start_time to calculate end_time
                try:
                    parsed_start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end_time = (parsed_start + timedelta(days=7)).isoformat().replace('+00:00', 'Z')
                except:
                    end_time = (now + timedelta(days=7)).isoformat().replace('+00:00', 'Z')
            else:
                # Validate that end_time is within 7 days of start_time
                try:
                    parsed_start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    parsed_end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    if (parsed_end - parsed_start).days > 7:
                        # Cap at 7 days
                        end_time = (parsed_start + timedelta(days=7)).isoformat().replace('+00:00', 'Z')
                except:
                    # If parsing fails, use default 7 days from start
                    try:
                        parsed_start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        end_time = (parsed_start + timedelta(days=7)).isoformat().replace('+00:00', 'Z')
                    except:
                        end_time = (now + timedelta(days=7)).isoformat().replace('+00:00', 'Z')
            
            logger.info(f"📅 Fetching available slots for event: {event_type_uri}")
            logger.info(f"   Start time: {start_time}")
            logger.info(f"   End time: {end_time}")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/event_type_available_times",
                    params={
                        "event_type": event_type_uri,
                        "start_time": start_time,
                        "end_time": end_time
                    },
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to get available slots: {response.text}")
                    raise Exception(f"Failed to get available slots: {response.text}")
                
                data = response.json()
                slots = data.get("collection", [])
                logger.info(f"✅ Found {len(slots)} available slots")
                return slots
                
        except Exception as e:
            logger.error(f"❌ Error getting available slots: {str(e)}")
            logger.exception(e)
            raise


# Global service instance
calendly_service = CalendlyService()