"""
Email Service for sending registration confirmations and lead generation emails
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.html import MIMEHtml
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails"""
    
    def __init__(self):
        # Email configuration from environment variables
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_username)
        self.from_name = os.getenv("FROM_NAME", "AI Background Remover")
        self.use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send an email
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content (optional, will be generated from HTML if not provided)
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if not self.smtp_username or not self.smtp_password:
            logger.warning("SMTP credentials not configured. Email not sent.")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email
            
            # Add plain text version
            if text_content:
                msg.attach(MIMEText(text_content, "plain", "utf-8"))
            
            # Add HTML version
            msg.attach(MIMEText(html_content, "html", "utf-8"))
            
            # Connect to SMTP server and send email
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            
            server.login(self.smtp_username, self.smtp_password)
            server.sendmail(self.from_email, to_email, msg.as_string())
            server.quit()
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    def send_welcome_email(self, to_email: str, first_name: str = "User") -> bool:
        """
        Send a welcome/thank you email after registration
        
        Args:
            to_email: Recipient email address
            first_name: User's first name
            
        Returns:
            bool: True if email was sent successfully
        """
        subject = "Welcome to AI Background Remover - Thank You for Registering!"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .container {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border-radius: 10px;
                    padding: 30px;
                    color: white;
                }}
                .logo {{
                    text-align: center;
                    margin-bottom: 20px;
                }}
                .logo-icon {{
                    font-size: 48px;
                    margin-bottom: 10px;
                }}
                h1 {{
                    color: white;
                    font-size: 28px;
                    margin-bottom: 10px;
                }}
                .content {{
                    background: white;
                    color: #333;
                    border-radius: 8px;
                    padding: 25px;
                    margin-top: 20px;
                }}
                .button {{
                    display: inline-block;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    text-decoration: none;
                    padding: 12px 30px;
                    border-radius: 5px;
                    margin-top: 20px;
                    font-weight: bold;
                }}
                .features {{
                    margin: 20px 0;
                }}
                .feature {{
                    padding: 10px 0;
                    border-bottom: 1px solid #eee;
                }}
                .feature:last-child {{
                    border-bottom: none;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 20px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    font-size: 12px;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">
                    <div class="logo-icon">🎨</div>
                    <h1>Welcome to AI Background Remover!</h1>
                </div>
                
                <div class="content">
                    <h2>Thank You for Registering, {first_name}! 🎉</h2>
                    
                    <p>We're excited to have you on board! Your account has been successfully created.</p>
                    
                    <p><strong>Enjoy</strong> our powerful AI-powered background removal tools:</p>
                    
                    <div class="features">
                        <div class="feature">✨ <strong>Instant Background Removal</strong> - Remove backgrounds from images in seconds</div>
                        <div class="feature">🎨 <strong>Background Replacement</strong> - Replace backgrounds with custom images or colors</div>
                        <div class="feature">👕 <strong>Clothes Enhancement</strong> - Change and enhance clothing in photos</div>
                        <div class="feature">🚀 <strong>High-Quality Results</strong> - Professional-grade output ready for any use</div>
                    </div>
                    
                    <div style="text-align: center;">
                        <a href="https://hintergrundentfernen.ai/dashboard" class="button">Go to Dashboard</a>
                    </div>
                    
                    <p style="margin-top: 20px;">Get started by uploading your first image and experiencing the magic of AI-powered editing!</p>
                </div>
                
                <div class="footer">
                    <p>This email was sent to {to_email}</p>
                    <p>&copy; 2024 AI Background Remover. All rights reserved.</p>
                    <p>Need help? Contact us at support@hintergrundentfernen.ai</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to AI Background Remover, {first_name}!
        
        Thank you for registering! We're excited to have you on board.
        
        Your account has been successfully created, and you can now start using our powerful AI-powered background removal tools.
        
        Features:
        - Instant Background Removal
        - Background Replacement
        - Clothes Enhancement
        - High-Quality Results
        
        Get started by visiting: https://hintergrundentfernen.ai/dashboard
        
        Need help? Contact us at support@hintergrundentfernen.ai
        
        © 2024 AI Background Remover. All rights reserved.
        """
        
        return self.send_email(to_email, subject, html_content, text_content)
    
    def send_verification_email(self, to_email: str, verification_token: str) -> bool:
        """
        Send email verification email
        
        Args:
            to_email: Recipient email address
            verification_token: Token for email verification
        """
        verification_link = f"https://hintergrundentfernen.ai/verify-email?token={verification_token}"
        
        subject = "Verify Your Email - AI Background Remover"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .container {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border-radius: 10px;
                    padding: 30px;
                    color: white;
                }}
                .content {{
                    background: white;
                    color: #333;
                    border-radius: 8px;
                    padding: 25px;
                    margin-top: 20px;
                }}
                .button {{
                    display: inline-block;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    text-decoration: none;
                    padding: 12px 30px;
                    border-radius: 5px;
                    margin-top: 20px;
                    font-weight: bold;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 20px;
                    font-size: 12px;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Verify Your Email</h1>
                <div class="content">
                    <p>Thank you for registering! Please verify your email address to complete your registration.</p>
                    <div style="text-align: center;">
                        <a href="{verification_link}" class="button">Verify Email</a>
                    </div>
                    <p style="margin-top: 20px;">Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #667eea;">{verification_link}</p>
                    <p style="margin-top: 20px;">This link will expire in 24 hours.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2024 AI Background Remover. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)


# Global email service instance
email_service = EmailService()
