import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# NOTE: For production, use environment variables for credentials
# For development/testing, this can be configured with your email provider
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "your-email@gmail.com"  # Change this
SENDER_PASSWORD = "your-app-password"  # Use app-specific password

def send_otp_email(recipient_email: str, otp: str) -> bool:
    """
    Send OTP via email
    Returns True if successful, False otherwise
    
    For Gmail:
    1. Enable 2FA
    2. Create app-specific password
    3. Use that password here
    """
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = "Your OTP Code"
        message["From"] = SENDER_EMAIL
        message["To"] = recipient_email

        # Plain text version
        text = f"""Your OTP code is: {otp}

This code will expire in 10 minutes.

If you didn't request this, please ignore this email."""

        # HTML version
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
                <div style="background-color: white; padding: 20px; border-radius: 8px; max-width: 400px; margin: 0 auto;">
                    <h2 style="color: #1f1f1f; margin-bottom: 20px;">Email Verification</h2>
                    <p style="color: #666; margin-bottom: 20px;">Your OTP code is:</p>
                    <div style="background-color: #f0f0f0; padding: 15px; border-radius: 6px; text-align: center; margin-bottom: 20px;">
                        <span style="font-size: 32px; font-weight: bold; color: #d90429; letter-spacing: 4px;">{otp}</span>
                    </div>
                    <p style="color: #999; font-size: 14px;">This code will expire in 10 minutes.</p>
                    <p style="color: #999; font-size: 14px;">If you didn't request this, please ignore this email.</p>
                </div>
            </body>
        </html>
        """

        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        message.attach(part1)
        message.attach(part2)

        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipient_email, message.as_string())

        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
