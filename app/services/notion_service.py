"""
Notion Integration Service
Fetches and processes content from Notion workspaces
Supports both OAuth and API key authentication
"""
import requests
from typing import List, Dict, Any, Optional
import os
import base64


class NotionService:
    def __init__(self):
        self.api_version = "2022-06-28"
        self.base_url = "https://api.notion.com/v1"
        self.oauth_base_url = "https://api.notion.com/v1/oauth"
    
    def _get_headers(self, api_key: str) -> Dict[str, str]:
        """Get headers for Notion API requests (supports both OAuth tokens and API keys)"""
        return {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": self.api_version,
            "Content-Type": "application/json"
        }

    def exchange_code_for_token(
        self,
        code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str
    ) -> Dict[str, Any]:
        """
        Exchange OAuth authorization code for access token
        This is called after user authorizes the app in Notion
        """
        try:
            # Encode client credentials
            credentials = f"{client_id}:{client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()

            # Exchange code for token
            response = requests.post(
                f"{self.oauth_base_url}/token",
                headers={
                    "Authorization": f"Basic {encoded_credentials}",
                    "Content-Type": "application/json"
                },
                json={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri
                },
                timeout=10
            )

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Token exchange failed: {response.status_code} - {response.text}"
                }

            token_data = response.json()

            return {
                "success": True,
                "access_token": token_data.get("access_token"),
                "workspace_id": token_data.get("workspace_id"),
                "workspace_name": token_data.get("workspace_name"),
                "workspace_icon": token_data.get("workspace_icon"),
                "bot_id": token_data.get("bot_id"),
                "owner": token_data.get("owner"),
                "duplicated_template_id": token_data.get("duplicated_template_id")
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error exchanging code for token: {str(e)}"
            }
    
    def test_connection(self, api_key: str) -> Dict[str, Any]:
        """Test Notion API connection"""
        try:
            response = requests.get(
                f"{self.base_url}/users/me",
                headers=self._get_headers(api_key),
                timeout=10
            )
            
            if response.status_code == 200:
                user_data = response.json()
                return {
                    "success": True,
                    "message": "Notion connection successful",
                    "user": user_data.get("name", "Unknown")
                }
            else:
                return {
                    "success": False,
                    "error": f"API returned {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Connection failed: {str(e)}"
            }
    
    def search_pages(self, api_key: str, query: str = "") -> Dict[str, Any]:
        """Search for pages in Notion workspace"""
        try:
            payload = {
                "filter": {
                    "value": "page",
                    "property": "object"
                }
            }
            
            if query:
                payload["query"] = query
            
            response = requests.post(
                f"{self.base_url}/search",
                headers=self._get_headers(api_key),
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Search failed: {response.status_code} - {response.text}"
                }
            
            data = response.json()
            pages = data.get("results", [])
            
            # Format pages for easy selection
            formatted_pages = []
            for page in pages:
                title = "Untitled"
                if page.get("properties"):
                    # Try to get title from properties
                    for prop_name, prop_value in page.get("properties", {}).items():
                        if prop_value.get("type") == "title" and prop_value.get("title"):
                            title_parts = prop_value.get("title", [])
                            if title_parts:
                                title = title_parts[0].get("plain_text", "Untitled")
                            break
                
                formatted_pages.append({
                    "id": page.get("id"),
                    "title": title,
                    "url": page.get("url"),
                    "created_time": page.get("created_time"),
                    "last_edited_time": page.get("last_edited_time")
                })
            
            return {
                "success": True,
                "pages": formatted_pages,
                "total": len(formatted_pages)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error searching pages: {str(e)}"
            }
    
    def get_page_content(self, api_key: str, page_id: str) -> Dict[str, Any]:
        """Get full content of a Notion page"""
        try:
            # Remove hyphens from page ID if present
            page_id = page_id.replace("-", "")
            
            print(f"📖 Fetching Notion page: {page_id}")
            
            # Get page metadata
            page_response = requests.get(
                f"{self.base_url}/pages/{page_id}",
                headers=self._get_headers(api_key),
                timeout=30
            )
            
            if page_response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Failed to fetch page: {page_response.status_code} - {page_response.text}"
                }
            
            page_data = page_response.json()
            
            # Get page title
            title = "Untitled Page"
            if page_data.get("properties"):
                for prop_name, prop_value in page_data.get("properties", {}).items():
                    if prop_value.get("type") == "title" and prop_value.get("title"):
                        title_parts = prop_value.get("title", [])
                        if title_parts:
                            title = title_parts[0].get("plain_text", "Untitled Page")
                        break
            
            # Get page blocks (content)
            blocks_response = requests.get(
                f"{self.base_url}/blocks/{page_id}/children",
                headers=self._get_headers(api_key),
                params={"page_size": 100},
                timeout=30
            )
            
            if blocks_response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Failed to fetch blocks: {blocks_response.status_code}"
                }
            
            blocks_data = blocks_response.json()
            blocks = blocks_data.get("results", [])
            
            # Convert blocks to text
            content = self._blocks_to_text(blocks)
            
            print(f"✅ Fetched Notion page: '{title}' ({len(content)} chars)")
            
            return {
                "success": True,
                "title": title,
                "content": content,
                "url": page_data.get("url"),
                "created_time": page_data.get("created_time"),
                "last_edited_time": page_data.get("last_edited_time"),
                "blocks_count": len(blocks)
            }
            
        except Exception as e:
            print(f"❌ Error fetching Notion page: {e}")
            return {
                "success": False,
                "error": f"Error: {str(e)}"
            }
    
    def get_database_content(self, api_key: str, database_id: str) -> Dict[str, Any]:
        """Get all pages from a Notion database"""
        try:
            database_id = database_id.replace("-", "")
            
            print(f"📊 Fetching Notion database: {database_id}")
            
            # Query database
            response = requests.post(
                f"{self.base_url}/databases/{database_id}/query",
                headers=self._get_headers(api_key),
                json={"page_size": 100},
                timeout=30
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Failed to fetch database: {response.status_code}"
                }
            
            data = response.json()
            pages = data.get("results", [])
            
            # Fetch content for each page
            all_content = []
            for page in pages:
                page_id = page.get("id")
                page_content = self.get_page_content(api_key, page_id)
                
                if page_content.get("success"):
                    all_content.append(page_content)
            
            # Combine all content
            combined_text = "\n\n".join([
                f"# {item['title']}\n\n{item['content']}" 
                for item in all_content
            ])
            
            return {
                "success": True,
                "pages": all_content,
                "total_pages": len(all_content),
                "combined_content": combined_text
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error fetching database: {str(e)}"
            }
    
    def _blocks_to_text(self, blocks: List[Dict]) -> str:
        """Convert Notion blocks to plain text"""
        text_parts = []
        
        for block in blocks:
            block_type = block.get("type")
            
            if block_type == "paragraph":
                text = self._extract_rich_text(block.get("paragraph", {}).get("rich_text", []))
                if text:
                    text_parts.append(text)
            
            elif block_type == "heading_1":
                text = self._extract_rich_text(block.get("heading_1", {}).get("rich_text", []))
                if text:
                    text_parts.append(f"\n# {text}\n")
            
            elif block_type == "heading_2":
                text = self._extract_rich_text(block.get("heading_2", {}).get("rich_text", []))
                if text:
                    text_parts.append(f"\n## {text}\n")
            
            elif block_type == "heading_3":
                text = self._extract_rich_text(block.get("heading_3", {}).get("rich_text", []))
                if text:
                    text_parts.append(f"\n### {text}\n")
            
            elif block_type == "bulleted_list_item":
                text = self._extract_rich_text(block.get("bulleted_list_item", {}).get("rich_text", []))
                if text:
                    text_parts.append(f"• {text}")
            
            elif block_type == "numbered_list_item":
                text = self._extract_rich_text(block.get("numbered_list_item", {}).get("rich_text", []))
                if text:
                    text_parts.append(f"1. {text}")
            
            elif block_type == "quote":
                text = self._extract_rich_text(block.get("quote", {}).get("rich_text", []))
                if text:
                    text_parts.append(f"> {text}")
            
            elif block_type == "code":
                text = self._extract_rich_text(block.get("code", {}).get("rich_text", []))
                language = block.get("code", {}).get("language", "")
                if text:
                    text_parts.append(f"```{language}\n{text}\n```")
            
            elif block_type == "callout":
                text = self._extract_rich_text(block.get("callout", {}).get("rich_text", []))
                if text:
                    text_parts.append(f"📌 {text}")
            
            elif block_type == "toggle":
                text = self._extract_rich_text(block.get("toggle", {}).get("rich_text", []))
                if text:
                    text_parts.append(text)
            
            elif block_type == "divider":
                text_parts.append("---")
        
        return "\n".join(text_parts)
    
    def _extract_rich_text(self, rich_text_array: List[Dict]) -> str:
        """Extract plain text from Notion rich text array"""
        if not rich_text_array:
            return ""
        
        text_parts = []
        for text_obj in rich_text_array:
            text_parts.append(text_obj.get("plain_text", ""))
        
        return "".join(text_parts)


# Global service instance
notion_service = NotionService()

