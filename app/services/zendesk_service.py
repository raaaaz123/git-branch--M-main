"""
Zendesk API service for handling OAuth and ticket operations
"""
import os
import httpx
import base64
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode


class ZendeskService:
    """Service for interacting with Zendesk API"""
    
    def __init__(self):
        self.client_id = os.getenv("ZENDESK_CLIENT_ID")
        self.client_secret = os.getenv("ZENDESK_CLIENT_SECRET")
        self.redirect_uri = os.getenv("ZENDESK_REDIRECT_URI")
        # Zendesk OAuth base URL - subdomain will be provided by user during OAuth
        # We'll use a generic URL structure that works with any subdomain
        self.oauth_base_url = "https://{subdomain}.zendesk.com"
        
    def get_oauth_url(self, subdomain: str = None, state: str = None) -> str:
        """Generate Zendesk OAuth authorization URL"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"🔗 Generating Zendesk OAuth URL")
            logger.info(f"   Client ID: {self.client_id[:10] if self.client_id else 'None'}...")
            logger.info(f"   Redirect URI: {self.redirect_uri}")
            logger.info(f"   Subdomain: {subdomain}")
            logger.info(f"   State: {state}")
            
            if not self.client_id:
                raise ValueError("ZENDESK_CLIENT_ID is not set in environment variables")
            if not self.redirect_uri:
                raise ValueError("ZENDESK_REDIRECT_URI is not set in environment variables")
            
            # If subdomain is not provided, we'll need to get it from user
            # For now, we'll use a placeholder that will be replaced
            if not subdomain:
                # In a real implementation, you might want to prompt for subdomain
                # For now, we'll use a generic approach
                raise ValueError("Subdomain is required for Zendesk OAuth")
            
            # Build OAuth URL parameters
            params = {
                "client_id": self.client_id,
                "response_type": "code",
                "redirect_uri": self.redirect_uri,
                "scope": "read write"
            }

            # Optional state parameter
            if state:
                params["state"] = state

            # Construct full authorization URL
            oauth_url = f"https://{subdomain}.zendesk.com/oauth/authorizations/new?{urlencode(params)}"
            logger.info(f"✅ OAuth URL generated: {oauth_url[:100]}...")
            return oauth_url

        except Exception as e:
            logger.error(f"❌ Error generating OAuth URL: {str(e)}")
            logger.exception(e)
            raise
    
    async def exchange_code_for_token(self, code: str, subdomain: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Create basic auth header
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://{subdomain}.zendesk.com/oauth/tokens",
                    json={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": self.redirect_uri,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret
                    },
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Basic {encoded_credentials}"
                    }
                )
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"❌ Failed to exchange code for token: {error_text}")
                    raise Exception(f"Failed to exchange code for token: {error_text}")
                
                token_data = response.json()
                logger.info(f"✅ Successfully exchanged code for token")
                return token_data
        except Exception as e:
            logger.error(f"❌ Error exchanging code for token: {str(e)}")
            raise
    
    async def get_current_user(self, access_token: str, subdomain: str) -> Dict[str, Any]:
        """Get current user information"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://{subdomain}.zendesk.com/api/v2/users/me.json",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"❌ Failed to get user info: {error_text}")
                    raise Exception(f"Failed to get user info: {error_text}")
                
                data = response.json()
                logger.info(f"✅ Successfully retrieved user info")
                return data.get("user", {})
        except Exception as e:
            logger.error(f"❌ Error getting user info: {str(e)}")
            raise
    
    async def create_ticket(self, access_token: str, subdomain: str, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a support ticket"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://{subdomain}.zendesk.com/api/v2/tickets.json",
                    json={"ticket": ticket_data},
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code not in [200, 201]:
                    error_text = response.text
                    logger.error(f"❌ Failed to create ticket: {error_text}")
                    raise Exception(f"Failed to create ticket: {error_text}")
                
                data = response.json()
                logger.info(f"✅ Successfully created ticket")
                return data.get("ticket", {})
        except Exception as e:
            logger.error(f"❌ Error creating ticket: {str(e)}")
            raise
    
    async def get_tickets(self, access_token: str, subdomain: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Get list of tickets"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://{subdomain}.zendesk.com/api/v2/tickets.json",
                    params={"per_page": limit},
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"❌ Failed to get tickets: {error_text}")
                    raise Exception(f"Failed to get tickets: {error_text}")
                
                data = response.json()
                logger.info(f"✅ Successfully retrieved tickets")
                return data.get("tickets", [])
        except Exception as e:
            logger.error(f"❌ Error getting tickets: {str(e)}")
            raise
    
    async def list_agents(self, access_token: str, subdomain: str) -> List[Dict[str, Any]]:
        """Get list of Zendesk agents (users with agent role)"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            async with httpx.AsyncClient() as client:
                # Get users with role 'agent' or 'admin'
                response = await client.get(
                    f"https://{subdomain}.zendesk.com/api/v2/users.json",
                    params={"role[]": ["agent", "admin"]},
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"❌ Failed to get agents: {error_text}")
                    raise Exception(f"Failed to get agents: {error_text}")
                
                data = response.json()
                logger.info(f"✅ Successfully retrieved agents")
                return data.get("users", [])
        except Exception as e:
            logger.error(f"❌ Error getting agents: {str(e)}")
            raise


# Create singleton instance
zendesk_service = ZendeskService()

