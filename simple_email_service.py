#!/usr/bin/env python3
"""
Simple standalone email service for ZeptoMail integration
"""
import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleEmailService:
    def __init__(self):
        self.base_url = "https://api.zeptomail.in/v1.1/email"
        self.headers = {
            'accept': "application/json",
            'content-type': "application/json",
            'authorization': "Zoho-enczapikey PHtE6r0LEOu6jWMspkIJ5f7tFMCgPdh6q+lnJAESsY9ACKNXG00HqIx9m2Dj+h4rAPgRHaWYz446sOnO4eOMczvvNzxNW2qyqK3sx/VYSPOZsbq6x00VslgTdEPZXY/pcdJj1S3UvtnTNA==",
        }
    
    def send_notification_email(self, 
                              to_email: str, 
                              to_name: str, 
                              subject: str, 
                              message_content: str,
                              sender_type: str = "customer",
                              customer_name: str = "",
                              business_name: str = "") -> dict:
        """
        Send notification email for new messages
        """
        try:
            # Create email template based on sender type
            if sender_type == "customer":
                html_body = self._create_customer_message_template(
                    message_content, customer_name, business_name
                )
            elif sender_type == "business":
                html_body = self._create_business_message_template(
                    message_content, business_name, customer_name
                )
            elif sender_type == "ai":
                html_body = self._create_ai_message_template(
                    message_content, customer_name, business_name
                )
            else:
                html_body = self._create_default_message_template(message_content)
            
            payload = {
                "from": {"address": "noreply@rexahire.com"},
                "to": [{"email_address": {"address": to_email, "name": to_name}}],
                "subject": subject,
                "htmlbody": html_body
            }
            
            response = requests.post(
                self.base_url, 
                data=json.dumps(payload), 
                headers=self.headers
            )
            
            if response.status_code == 200:
                logger.info(f"Email sent successfully to {to_email}")
                return {"success": True, "message": "Email sent successfully"}
            else:
                logger.error(f"Failed to send email: {response.text}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _create_customer_message_template(self, message: str, customer_name: str, business_name: str) -> str:
        """Create HTML template for customer messages"""
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                <h2 style="color: #333; margin-bottom: 20px;">New Message from Customer</h2>
                <div style="background-color: white; padding: 20px; border-radius: 8px; border-left: 4px solid #007bff;">
                    <p style="margin: 0 0 10px 0;"><strong>From:</strong> {customer_name}</p>
                    <p style="margin: 0 0 10px 0;"><strong>To:</strong> {business_name}</p>
                    <div style="margin-top: 15px;">
                        <p style="margin: 0; font-size: 16px; line-height: 1.5;">{message}</p>
                    </div>
                </div>
                <p style="color: #666; font-size: 14px; margin-top: 20px;">
                    Reply to this conversation in your dashboard to continue the chat.
                </p>
            </div>
        </div>
        """
    
    def _create_business_message_template(self, message: str, business_name: str, customer_name: str) -> str:
        """Create HTML template for business messages"""
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                <h2 style="color: #333; margin-bottom: 20px;">Reply from {business_name}</h2>
                <div style="background-color: white; padding: 20px; border-radius: 8px; border-left: 4px solid #28a745;">
                    <p style="margin: 0 0 10px 0;"><strong>From:</strong> {business_name}</p>
                    <p style="margin: 0 0 10px 0;"><strong>To:</strong> {customer_name}</p>
                    <div style="margin-top: 15px;">
                        <p style="margin: 0; font-size: 16px; line-height: 1.5;">{message}</p>
                    </div>
                </div>
                <p style="color: #666; font-size: 14px; margin-top: 20px;">
                    You can continue this conversation by visiting the chat widget.
                </p>
            </div>
        </div>
        """
    
    def _create_ai_message_template(self, message: str, customer_name: str, business_name: str) -> str:
        """Create HTML template for AI messages"""
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                <h2 style="color: #333; margin-bottom: 20px;">AI Assistant Response</h2>
                <div style="background-color: white; padding: 20px; border-radius: 8px; border-left: 4px solid #6f42c1;">
                    <p style="margin: 0 0 10px 0;"><strong>AI Assistant replied to:</strong> {customer_name}</p>
                    <p style="margin: 0 0 10px 0;"><strong>Business:</strong> {business_name}</p>
                    <div style="margin-top: 15px;">
                        <p style="margin: 0; font-size: 16px; line-height: 1.5;">{message}</p>
                    </div>
                    <div style="background-color: #e9ecef; padding: 10px; border-radius: 4px; margin-top: 15px;">
                        <p style="margin: 0; font-size: 12px; color: #666;">
                            🤖 This message was generated by AI Assistant
                        </p>
                    </div>
                </div>
                <p style="color: #666; font-size: 14px; margin-top: 20px;">
                    The AI assistant has responded to your customer. You can continue the conversation in your dashboard.
                </p>
            </div>
        </div>
        """
    
    def _create_default_message_template(self, message: str) -> str:
        """Create default HTML template for messages"""
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                <h2 style="color: #333; margin-bottom: 20px;">New Message</h2>
                <div style="background-color: white; padding: 20px; border-radius: 8px;">
                    <p style="margin: 0; font-size: 16px; line-height: 1.5;">{message}</p>
                </div>
            </div>
        </div>
        """

# Global email service instance
email_service = SimpleEmailService()

def test_email():
    """Test function for email service"""
    print("Testing email service...")
    
    result = email_service.send_notification_email(
        to_email="support@rexahire.com",
        to_name="Test User",
        subject="Test Email from AI Native CRM",
        message_content="This is a test email to verify the email service is working correctly.",
        sender_type="customer",
        customer_name="Test Customer",
        business_name="Test Business"
    )
    
    print(f"Email result: {result}")
    
    if result["success"]:
        print("✅ Email sent successfully!")
    else:
        print(f"❌ Email failed: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    test_email()
