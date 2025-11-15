"""
WhatsApp Business API service for handling OAuth and messaging operations
"""
import os
import httpx
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode


class WhatsAppService:
    """Service for interacting with WhatsApp Business API (Meta)"""
    
    def __init__(self):
        self.app_id = os.getenv("META_APP_ID")  # Facebook/Meta App ID
        self.app_secret = os.getenv("META_APP_SECRET")  # Facebook/Meta App Secret
        self.redirect_uri = os.getenv("WHATSAPP_REDIRECT_URI")
        self.graph_api_version = "18.0"  # Meta Graph API version (without 'v' prefix)
        
    def get_oauth_url(self, state: str = None, fallback_redirect_uri: str = None, domain: str = None, use_popup: bool = True) -> str:
        """Generate Meta OAuth authorization URL for WhatsApp"""
        import logging
        import time
        import secrets
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"🔗 Generating WhatsApp OAuth URL")
            logger.info(f"   App ID: {self.app_id[:10] if self.app_id else 'None'}...")
            logger.info(f"   Redirect URI: {self.redirect_uri}")
            logger.info(f"   Use Popup: {use_popup}")
            logger.info(f"   State: {state}")
            
            if not self.app_id:
                raise ValueError("META_APP_ID is not set in environment variables")
            if not self.redirect_uri:
                raise ValueError("WHATSAPP_REDIRECT_URI is not set in environment variables")
            
            # Use fallback_redirect_uri if provided, otherwise use default redirect_uri
            actual_callback_uri = fallback_redirect_uri or self.redirect_uri
            
            if use_popup:
                # Extract domain from redirect URI for xd_arbiter
                if not domain:
                    from urllib.parse import urlparse
                    parsed = urlparse(actual_callback_uri)
                    if parsed.netloc:
                        domain = parsed.netloc
                    else:
                        # Default to localhost:3000 for development
                        domain = 'localhost:3000'
                
                # Generate callback identifiers for xd_arbiter
                callback_id = secrets.token_hex(8)
                frame_id = secrets.token_hex(8)
                logger_id = secrets.token_hex(8)
                cbt = int(time.time() * 1000)  # Current timestamp in milliseconds
                
                # Build xd_arbiter redirect URI (Facebook's popup handler)
                xd_arbiter_base = f"https://staticxx.facebook.com/x/connect/xd_arbiter/?version=46"
                xd_arbiter_params = {
                    "cb": callback_id,
                    "domain": domain,
                    "is_canvas": "false",
                    "origin": f"https://{domain}/" + secrets.token_hex(8),
                    "relation": "opener",
                    "frame": frame_id
                }
                xd_arbiter_redirect = f"{xd_arbiter_base}#" + "&".join([f"{k}={v}" for k, v in xd_arbiter_params.items()])
                
                # Build channel URL for xd_arbiter
                channel_cb = secrets.token_hex(8)
                channel_params = {
                    "cb": channel_cb,
                    "domain": domain,
                    "is_canvas": "false",
                    "origin": f"https://{domain}/" + secrets.token_hex(8),
                    "relation": "opener"
                }
                channel_url = f"{xd_arbiter_base}#" + "&".join([f"{k}={v}" for k, v in channel_params.items()])
                
                # Build OAuth URL parameters for WhatsApp Business (popup mode)
                params = {
                    "app_id": self.app_id,
                    "client_id": self.app_id,
                    "cbt": str(cbt),
                    "channel_url": channel_url,
                    "config_id": secrets.token_hex(8),  # Config ID
                    "display": "popup",
                    "domain": domain,
                    "e2e": "{}",
                    "extras": '{"sessionInfoVersion":2}',
                    "fallback_redirect_uri": actual_callback_uri,
                    "locale": "en_US",
                    "logger_id": logger_id,
                    "origin": "1",
                    "override_default_response_type": "true",
                    "redirect_uri": xd_arbiter_redirect,
                    "response_type": "code",
                    "scope": "whatsapp_business_management,whatsapp_business_messaging,business_management",
                    "sdk": "joey",
                    "version": self.graph_api_version
                }
            else:
                # Simple OAuth flow (fallback mode)
                params = {
                    "client_id": self.app_id,
                    "redirect_uri": actual_callback_uri,
                    "response_type": "code",
                    "scope": "whatsapp_business_management,whatsapp_business_messaging,business_management",
                    "display": "page"
                }

            # Optional state parameter
            if state:
                params["state"] = state

            # Construct full authorization URL
            oauth_url = f"https://www.facebook.com/v{self.graph_api_version}/dialog/oauth?{urlencode(params)}"
            logger.info(f"✅ OAuth URL generated ({'popup' if use_popup else 'page'} mode): {oauth_url[:150]}...")
            return oauth_url

        except Exception as e:
            logger.error(f"❌ Error generating OAuth URL: {str(e)}")
            logger.exception(e)
            raise
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://graph.facebook.com/v{self.graph_api_version}/oauth/access_token",
                    params={
                        "client_id": self.app_id,
                        "client_secret": self.app_secret,
                        "redirect_uri": self.redirect_uri,
                        "code": code
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
    
    async def get_business_accounts(self, access_token: str) -> List[Dict[str, Any]]:
        """Get WhatsApp Business Accounts"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://graph.facebook.com/v{self.graph_api_version}/me/businesses",
                    params={
                        "access_token": access_token,
                        "fields": "id,name"
                    }
                )
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"❌ Failed to get business accounts: {error_text}")
                    raise Exception(f"Failed to get business accounts: {error_text}")
                
                data = response.json()
                logger.info(f"✅ Successfully retrieved business accounts")
                return data.get("data", [])
        except Exception as e:
            logger.error(f"❌ Error getting business accounts: {str(e)}")
            raise
    
    async def get_phone_numbers(self, access_token: str, business_account_id: str) -> List[Dict[str, Any]]:
        """Get phone numbers associated with WhatsApp Business Account"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://graph.facebook.com/v{self.graph_api_version}/{business_account_id}/phone_numbers",
                    params={
                        "access_token": access_token,
                        "fields": "id,display_phone_number,verified_name,quality_rating"
                    }
                )
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"❌ Failed to get phone numbers: {error_text}")
                    raise Exception(f"Failed to get phone numbers: {error_text}")
                
                data = response.json()
                logger.info(f"✅ Successfully retrieved phone numbers")
                return data.get("data", [])
        except Exception as e:
            logger.error(f"❌ Error getting phone numbers: {str(e)}")
            raise
    
    async def send_message(
        self, 
        access_token: str, 
        phone_number_id: str,
        to: str,
        message: str
    ) -> Dict[str, Any]:
        """Send WhatsApp message"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://graph.facebook.com/v{self.graph_api_version}/{phone_number_id}/messages",
                    json={
                        "messaging_product": "whatsapp",
                        "to": to,
                        "type": "text",
                        "text": {
                            "body": message
                        }
                    },
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code not in [200, 201]:
                    error_text = response.text
                    logger.error(f"❌ Failed to send message: {error_text}")
                    raise Exception(f"Failed to send message: {error_text}")
                
                data = response.json()
                logger.info(f"✅ Successfully sent message")
                return data
        except Exception as e:
            logger.error(f"❌ Error sending message: {str(e)}")
            raise


# Create singleton instance
whatsapp_service = WhatsAppService()

