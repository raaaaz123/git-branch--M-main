#!/usr/bin/env python3
"""
Simple HTTP server for email notifications
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.parse
from simple_email_service import email_service

class EmailHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/email/send-notification':
            self.send_email_notification()
        elif self.path == '/api/email/test':
            self.test_email()
        else:
            self.send_error(404, "Not Found")
    
    def do_GET(self):
        if self.path == '/api/health':
            self.send_health_response()
        else:
            self.send_error(404, "Not Found")
    
    def send_email_notification(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Determine recipient based on sender type
            if data['senderType'] == 'customer':
                # Customer sent message, notify business
                recipient_email = data['businessEmail']
                recipient_name = data['businessName']
                subject = f"New message from {data['customerName']}"
            elif data['senderType'] in ['business', 'ai']:
                # Business or AI sent message, notify customer
                recipient_email = data['customerEmail']
                recipient_name = data['customerName']
                if data['senderType'] == 'ai':
                    subject = f"AI Assistant replied to your message"
                else:
                    subject = f"Reply from {data['businessName']}"
            else:
                self.send_error(400, "Invalid sender type")
                return
            
            # Send email notification
            result = email_service.send_notification_email(
                to_email=recipient_email,
                to_name=recipient_name,
                subject=subject,
                message_content=data['message'],
                sender_type=data['senderType'],
                customer_name=data['customerName'],
                business_name=data['businessName']
            )
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            response = {"success": True, "message": "Email notification sent successfully"}
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_error(500, f"Internal server error: {str(e)}")
    
    def test_email(self):
        try:
            result = email_service.send_notification_email(
                to_email="support@rexahire.com",
                to_name="Test User",
                subject="Test Email from AI Native CRM",
                message_content="This is a test email to verify the email service is working correctly.",
                sender_type="customer",
                customer_name="Test Customer",
                business_name="Test Business"
            )
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps(result).encode())
            
        except Exception as e:
            self.send_error(500, f"Internal server error: {str(e)}")
    
    def send_health_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {"status": "healthy", "service": "email-service"}
        self.wfile.write(json.dumps(response).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def run_server(port=8001):
    server_address = ('', port)
    httpd = HTTPServer(server_address, EmailHandler)
    print(f"🚀 Simple Email Server running on http://localhost:{port}")
    print(f"📧 Email service ready for ZeptoMail integration")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
