#!/usr/bin/env python3
"""
DEPRECATED: This server is deprecated. Email notifications are now handled via Next.js API routes using SendPulse.
See: app/api/emails/message-notification/route.ts

This file is kept for reference only and should not be used.
"""
# DEPRECATED - Email notifications are now handled via Next.js API routes using SendPulse
# See: app/api/emails/message-notification/route.ts

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.parse

# Note: simple_email_service is deprecated - emails now use SendPulse via Next.js API routes

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
            
            # DEPRECATED: Email sending is now handled via Next.js API routes
            # This endpoint should not be used - use app/api/emails/message-notification/route.ts instead
            result = {"success": False, "error": "This endpoint is deprecated. Use Next.js API routes instead."}
            
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
            # DEPRECATED: Email sending is now handled via Next.js API routes
            result = {"success": False, "error": "This endpoint is deprecated. Use Next.js API routes instead."}
            
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
    print(f"⚠️  DEPRECATED: This server is deprecated. Use Next.js API routes with SendPulse instead.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
