"""
Cloudflare R2 Storage Service
"""
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import os
from typing import Optional, Dict, Any
import uuid
from datetime import datetime

# R2 Configuration
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "rexa-documents")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "")  # Optional: Custom domain for R2


class R2Service:
    def __init__(self):
        """Initialize R2 client using S3-compatible API"""
        self.client = None
        self.bucket_name = R2_BUCKET_NAME
        self.public_url = R2_PUBLIC_URL
        
        if R2_ACCOUNT_ID and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY:
            try:
                # R2 endpoint format: https://<account_id>.r2.cloudflarestorage.com
                endpoint_url = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
                
                self.client = boto3.client(
                    's3',
                    endpoint_url=endpoint_url,
                    aws_access_key_id=R2_ACCESS_KEY_ID,
                    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
                    config=Config(signature_version='s3v4'),
                    region_name='auto'  # R2 uses 'auto' for region
                )
                
                print(f"✅ R2 Storage initialized: {self.bucket_name}")
            except Exception as e:
                print(f"⚠️ R2 Storage initialization failed: {e}")
                self.client = None
        else:
            print("⚠️ R2 credentials not configured")
    
    def upload_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        workspace_id: Optional[str] = None,
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload file to R2 storage in documents folder
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            content_type: MIME type of the file
            workspace_id: Optional workspace ID for organization
            agent_id: Optional agent ID for organization
            
        Returns:
            Dict with success status, file_url, and file_key
        """
        if not self.client:
            return {
                "success": False,
                "error": "R2 client not initialized"
            }
        
        try:
            # Generate unique filename to avoid collisions
            file_extension = os.path.splitext(filename)[1]
            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            
            # Store all files in documents/ folder (no subfolders)
            file_key = f"documents/{unique_filename}"
            
            # Upload to R2
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=file_key,
                Body=file_content,
                ContentType=content_type,
                Metadata={
                    'original_filename': filename,
                    'workspace_id': workspace_id or '',
                    'agent_id': agent_id or '',
                    'uploaded_at': datetime.utcnow().isoformat()
                }
            )
            
            # Generate public URL
            if self.public_url:
                # Use custom domain if configured
                file_url = f"{self.public_url}/{file_key}"
            else:
                # Use R2 public URL format
                file_url = f"https://{self.bucket_name}.{R2_ACCOUNT_ID}.r2.cloudflarestorage.com/{file_key}"
            
            print(f"✅ File uploaded to R2: {file_key}")
            
            return {
                "success": True,
                "file_url": file_url,
                "file_key": file_key,
                "original_filename": filename
            }
            
        except ClientError as e:
            error_msg = f"R2 upload failed: {e}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error during R2 upload: {e}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
    
    def delete_file(self, file_key: str) -> Dict[str, Any]:
        """
        Delete file from R2 storage
        
        Args:
            file_key: The key/path of the file in R2
            
        Returns:
            Dict with success status
        """
        if not self.client:
            return {
                "success": False,
                "error": "R2 client not initialized"
            }
        
        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=file_key
            )
            
            print(f"✅ File deleted from R2: {file_key}")
            
            return {
                "success": True,
                "message": f"File {file_key} deleted successfully"
            }
            
        except ClientError as e:
            error_msg = f"R2 delete failed: {e}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error during R2 delete: {e}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
    
    def get_file_url(self, file_key: str) -> str:
        """
        Get public URL for a file
        
        Args:
            file_key: The key/path of the file in R2
            
        Returns:
            Public URL string
        """
        if self.public_url:
            return f"{self.public_url}/{file_key}"
        else:
            return f"https://{self.bucket_name}.{R2_ACCOUNT_ID}.r2.cloudflarestorage.com/{file_key}"


# Global R2 service instance
r2_service = R2Service()
