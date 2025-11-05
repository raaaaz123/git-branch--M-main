"""
Google Sheets integration service
Handles OAuth and data fetching from Google Sheets
"""
import requests
from typing import Dict, Any, List
import base64


class GoogleSheetsService:
    def __init__(self):
        self.oauth_base_url = "https://oauth2.googleapis.com"
        self.sheets_api_base_url = "https://sheets.googleapis.com/v4"
        self.drive_api_base_url = "https://www.googleapis.com/drive/v3"

    def exchange_code_for_token(
        self,
        code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str
    ) -> Dict[str, Any]:
        """
        Exchange OAuth authorization code for access token

        Returns:
            {
                "success": True/False,
                "access_token": "...",
                "refresh_token": "...",
                "expires_in": 3600,
                "token_type": "Bearer",
                "error": "..." (if failed)
            }
        """
        try:
            response = requests.post(
                f"{self.oauth_base_url}/token",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                }
            )

            if not response.ok:
                error_data = response.json() if response.text else {}
                return {
                    "success": False,
                    "error": error_data.get("error_description", "Failed to exchange code for token")
                }

            data = response.json()

            return {
                "success": True,
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "expires_in": data.get("expires_in"),
                "token_type": data.get("token_type", "Bearer"),
                "scope": data.get("scope")
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error during token exchange: {str(e)}"
            }

    def list_spreadsheets(self, access_token: str, query: str = "") -> Dict[str, Any]:
        """
        List Google Sheets files from Google Drive

        Returns:
            {
                "success": True/False,
                "spreadsheets": [
                    {
                        "id": "spreadsheet_id",
                        "name": "spreadsheet_name",
                        "url": "https://docs.google.com/spreadsheets/d/...",
                        "modifiedTime": "2024-01-01T00:00:00.000Z"
                    }
                ],
                "error": "..." (if failed)
            }
        """
        try:
            # Build query to find Google Sheets files
            drive_query = "mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
            if query:
                drive_query += f" and name contains '{query}'"

            response = requests.get(
                f"{self.drive_api_base_url}/files",
                headers={
                    "Authorization": f"Bearer {access_token}"
                },
                params={
                    "q": drive_query,
                    "fields": "files(id,name,modifiedTime,webViewLink)",
                    "orderBy": "modifiedTime desc",
                    "pageSize": 100
                }
            )

            if not response.ok:
                error_data = response.json() if response.text else {}
                return {
                    "success": False,
                    "error": error_data.get("error", {}).get("message", "Failed to list spreadsheets")
                }

            data = response.json()
            files = data.get("files", [])

            spreadsheets = [
                {
                    "id": file.get("id"),
                    "name": file.get("name"),
                    "url": file.get("webViewLink", f"https://docs.google.com/spreadsheets/d/{file.get('id')}"),
                    "modifiedTime": file.get("modifiedTime")
                }
                for file in files
            ]

            return {
                "success": True,
                "spreadsheets": spreadsheets,
                "total": len(spreadsheets)
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error listing spreadsheets: {str(e)}"
            }

    def get_spreadsheet_data(
        self,
        access_token: str,
        spreadsheet_id: str,
        sheet_name: str = None
    ) -> Dict[str, Any]:
        """
        Get data from a Google Sheet

        Returns:
            {
                "success": True/False,
                "title": "Spreadsheet Title",
                "sheets": ["Sheet1", "Sheet2", ...],
                "data": [[row1], [row2], ...],
                "content": "formatted text content",
                "error": "..." (if failed)
            }
        """
        try:
            # First, get spreadsheet metadata
            metadata_response = requests.get(
                f"{self.sheets_api_base_url}/spreadsheets/{spreadsheet_id}",
                headers={
                    "Authorization": f"Bearer {access_token}"
                },
                params={
                    "fields": "properties,sheets.properties"
                }
            )

            if not metadata_response.ok:
                error_data = metadata_response.json() if metadata_response.text else {}
                return {
                    "success": False,
                    "error": error_data.get("error", {}).get("message", "Failed to fetch spreadsheet metadata")
                }

            metadata = metadata_response.json()
            title = metadata.get("properties", {}).get("title", "Untitled")
            sheets = [sheet["properties"]["title"] for sheet in metadata.get("sheets", [])]

            # Determine which sheet to fetch
            target_sheet = sheet_name if sheet_name else (sheets[0] if sheets else "Sheet1")

            # Fetch sheet data
            data_response = requests.get(
                f"{self.sheets_api_base_url}/spreadsheets/{spreadsheet_id}/values/{target_sheet}",
                headers={
                    "Authorization": f"Bearer {access_token}"
                }
            )

            if not data_response.ok:
                error_data = data_response.json() if data_response.text else {}
                return {
                    "success": False,
                    "error": error_data.get("error", {}).get("message", "Failed to fetch sheet data")
                }

            data_result = data_response.json()
            values = data_result.get("values", [])

            # Convert data to formatted text content
            content = self._format_sheet_data_as_text(title, target_sheet, values)

            return {
                "success": True,
                "title": title,
                "sheets": sheets,
                "data": values,
                "content": content,
                "rows_count": len(values),
                "sheet_name": target_sheet
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error fetching spreadsheet data: {str(e)}"
            }

    def _format_sheet_data_as_text(
        self,
        spreadsheet_title: str,
        sheet_name: str,
        data: List[List[str]]
    ) -> str:
        """
        Format spreadsheet data as readable text for RAG
        """
        if not data:
            return f"# {spreadsheet_title} - {sheet_name}\n\nThis sheet is empty."

        lines = []
        lines.append(f"# {spreadsheet_title}")
        lines.append(f"## Sheet: {sheet_name}")
        lines.append("")

        # Assume first row is headers
        if len(data) > 0:
            headers = data[0]
            lines.append("| " + " | ".join(str(h) for h in headers) + " |")
            lines.append("|" + "|".join(["---"] * len(headers)) + "|")

            # Add data rows
            for row in data[1:]:
                # Pad row to match header length
                padded_row = row + [""] * (len(headers) - len(row))
                lines.append("| " + " | ".join(str(cell) for cell in padded_row[:len(headers)]) + " |")

        return "\n".join(lines)


# Create singleton instance
google_sheets_service = GoogleSheetsService()
