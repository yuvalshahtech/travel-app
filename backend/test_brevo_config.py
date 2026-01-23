#!/usr/bin/env python3
"""
Quick test script to verify Brevo email sending.
Tests the configuration and sends a real email WITHOUT creating a signup.
"""

import os
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_brevo_email():
    """Test Brevo email configuration and send a test email."""
    
    logger.info("=" * 60)
    logger.info("Brevo Email Configuration Test")
    logger.info("=" * 60)
    
    # Check environment variables
    brevo_key = os.getenv("BREVO_API_KEY")
    sender_email = os.getenv("SENDER_EMAIL")
    sender_name = os.getenv("SENDER_NAME", "Travel App")
    
    logger.info(f"\n1. Checking environment variables:")
    logger.info(f"   BREVO_API_KEY: {'✓ SET' if brevo_key else '✗ NOT SET'}")
    logger.info(f"   SENDER_EMAIL: {sender_email if sender_email else '✗ NOT SET'}")
    logger.info(f"   SENDER_NAME: {sender_name}")
    
    if not brevo_key or not sender_email:
        logger.error("\n✗ Missing required environment variables!")
        logger.error("   Run: setx BREVO_API_KEY 'your-api-key'")
        logger.error("   Run: setx SENDER_EMAIL 'your-verified-email@gmail.com'")
        return False
    
    logger.info("\n2. Importing Brevo SDK...")
    try:
        import sib_api_v3_sdk
        from sib_api_v3_sdk.rest import ApiException
        logger.info("   ✓ Brevo SDK imported successfully")
    except ImportError as e:
        logger.error(f"   ✗ Failed to import Brevo SDK: {e}")
        logger.error("   Run: pip install sib-api-v3-sdk")
        return False
    
    logger.info("\n3. Testing Brevo API connection...")
    try:
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = brevo_key
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )
        logger.info("   ✓ Brevo API client configured")
    except Exception as e:
        logger.error(f"   ✗ Failed to configure API: {e}")
        return False
    
    logger.info("\n4. Sending test OTP email...")
    
    # Test OTP (not a real one)
    test_otp = "123456"
    test_recipient = sender_email  # Send to self
    
    try:
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": test_recipient}],
            sender={"email": sender_email, "name": sender_name},
            subject="[TEST] Your OTP Code for Signing In",
            html_content=f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>Test OTP Email</h2>
                    <p>If you received this, Brevo is working correctly!</p>
                    <p><strong>Test OTP: {test_otp}</strong></p>
                    <p style="color: #999; font-size: 12px;">Sent at: {datetime.now().isoformat()}</p>
                </body>
            </html>
            """,
            text_content=f"Test OTP: {test_otp}\nSent at: {datetime.now().isoformat()}"
        )
        
        response = api_instance.send_transac_email(send_smtp_email)
        
        logger.info(f"   ✓ Email submitted to Brevo")
        logger.info(f"   Message ID: {response.message_id if hasattr(response, 'message_id') else 'N/A'}")
        logger.info(f"\n5. Check your email ({test_recipient}) for the test message!")
        logger.info("   (May take 5-30 seconds to arrive)")
        
        return True
        
    except ApiException as e:
        logger.error(f"   ✗ Brevo API Error:")
        logger.error(f"      Status: {e.status}")
        logger.error(f"      Reason: {e.reason}")
        logger.error(f"      Body: {e.http_body}")
        return False
    except Exception as e:
        logger.error(f"   ✗ Error: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    success = test_brevo_email()
    sys.exit(0 if success else 1)
