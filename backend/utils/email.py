import os
import re
import logging
import threading
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

# Configure logging for email debugging
logger = logging.getLogger(__name__)

# ✅ Use environment variables for credentials
BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_NAME = os.getenv("SENDER_NAME", "Travel App")
DEV_MODE = os.getenv("DEV_MODE", "false").lower() in ("1", "true", "yes")

logger.info(f"ENV CHECK → BREVO_API_KEY loaded: {bool(BREVO_API_KEY)}")
logger.info(f"ENV CHECK → SENDER_EMAIL: {SENDER_EMAIL}")

def send_otp_email(recipient_email: str, otp: str) -> bool:
    """
    Send OTP via Brevo Transactional Email API.
    
    Returns True if successfully submitted to Brevo.
    Returns False and logs errors if Brevo rejects or API fails.
    
    CRITICAL: Does NOT return OTP. Must be delivered via Brevo only.
    """
    
    # Validate configuration
    if not BREVO_API_KEY:
        logger.error("BREVO_API_KEY environment variable not set")
        return False
    
    if not SENDER_EMAIL:
        logger.error("SENDER_EMAIL environment variable not set")
        return False
    
    logger.info(f"Preparing OTP email: recipient={recipient_email}, sender={SENDER_EMAIL}")

    try:
        # Configure Brevo API client
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = BREVO_API_KEY
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

        # Plain text version
        text_content = f"""Your OTP code is: {otp}

This code will expire in 10 minutes.

If you didn't request this, please ignore this email."""

        # HTML version
        html_content = f"""
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

        # Create email object with all mandatory Brevo fields
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": recipient_email}],
            sender={"email": SENDER_EMAIL, "name": SENDER_NAME},
            subject="Your OTP Code for Signing In",
            html_content=html_content,
            text_content=text_content
        )

        logger.debug(f"SendSmtpEmail object created: to={recipient_email}, sender_email={SENDER_EMAIL}")

        # Send email via Brevo API
        response = api_instance.send_transac_email(send_smtp_email)
        
        # Log successful response
        logger.info(f"Brevo API response: {response}")
        logger.info(f"Email message ID from Brevo: {getattr(response, 'message_id', 'N/A')}")
        
        return True

    except ApiException as e:
        # Log detailed API exception
        logger.error("Brevo API exception occurred while sending OTP email")
        logger.error(f"  Status code: {getattr(e, 'status', 'unknown')}")
        logger.error(f"  Reason: {getattr(e, 'reason', 'unknown')}")
        logger.error(f"  Body: {getattr(e, 'body', 'unknown')}")
        if DEV_MODE:
            logger.info(f"DEV_MODE enabled — OTP for {recipient_email}: {otp}")
        return False
        
    except Exception as e:
        # Log any other exceptions
        logger.error(f"Unexpected error sending OTP email: {type(e).__name__}: {e}", exc_info=True)
        if DEV_MODE:
            logger.info(f"DEV_MODE enabled — OTP for {recipient_email}: {otp}")
        return False

def send_booking_confirmation_email(
    to_email: str,
    user_name: str,
    hotel_name: str,
    check_in_date: str,
    check_out_date: str
) -> bool:
    """
    Send booking confirmation email via Brevo Transactional Email API.

    CRITICAL: Dates MUST be in YYYY-MM-DD format (user-selected dates, no timezone conversion)
    
    Args:
        to_email: Recipient email address
        user_name: Guest name
        hotel_name: Hotel name
        check_in_date: Check-in date in YYYY-MM-DD format (REQUIRED)
        check_out_date: Check-out date in YYYY-MM-DD format (REQUIRED)

    Returns True if successfully submitted to Brevo.
    Returns False and logs errors if Brevo rejects or API fails.
    """
    # VALIDATION: Ensure dates are present and in correct format
    if not check_in_date or not check_out_date:
        error_msg = f"CRITICAL: Missing dates in booking confirmation. check_in={check_in_date}, check_out={check_out_date}"
        logger.error(error_msg)
        print(f"[CRITICAL ERROR] {error_msg}")
        return False
    
    # VALIDATION: Dates must be strings in YYYY-MM-DD format
    if not isinstance(check_in_date, str) or not isinstance(check_out_date, str):
        error_msg = f"CRITICAL: Dates must be strings. Got check_in={type(check_in_date).__name__}, check_out={type(check_out_date).__name__}"
        logger.error(error_msg)
        print(f"[CRITICAL ERROR] {error_msg}")
        return False
    
    # VALIDATION: Check date format (should be YYYY-MM-DD)
    date_pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(date_pattern, check_in_date) or not re.match(date_pattern, check_out_date):
        error_msg = f"CRITICAL: Dates must be in YYYY-MM-DD format. Got check_in={check_in_date}, check_out={check_out_date}"
        logger.error(error_msg)
        print(f"[CRITICAL ERROR] {error_msg}")
        return False
    
    print("\n" + "="*80)
    print(f"[BOOKING EMAIL] Sending confirmation email")
    print(f"[BOOKING EMAIL] Recipient: {to_email}")
    print(f"[BOOKING EMAIL] Guest: {user_name}")
    print(f"[BOOKING EMAIL] Hotel: {hotel_name}")
    print(f"[BOOKING EMAIL] Check-in: {check_in_date}")
    print(f"[BOOKING EMAIL] Check-out: {check_out_date}")
    print(f"[BOOKING EMAIL] ✓ Dates validated - exact user-selected dates")
    print("="*80 + "\n")
    
    logger.info(f"[BOOKING EMAIL] Sending confirmation: {to_email} | Hotel: {hotel_name} | Dates: {check_in_date} to {check_out_date}")

    # ENVIRONMENT VALIDATION
    logger.info(f"BREVO_API_KEY present: {bool(BREVO_API_KEY)}")
    logger.info(f"SENDER_EMAIL: {SENDER_EMAIL}")
    
    if not BREVO_API_KEY:
        error_msg = "BREVO_API_KEY environment variable not set"
        logger.error(error_msg)
        print(f"[CRITICAL ERROR] {error_msg}")
        return False

    if not SENDER_EMAIL:
        error_msg = "SENDER_EMAIL environment variable not set"
        logger.error(error_msg)
        print(f"[CRITICAL ERROR] {error_msg}")
        return False

    safe_name = user_name.strip() or "Guest"

    subject = "Booking Confirmed!"
    text_content = (
        f"Dear {safe_name},\n\n"
        f"Your booking at {hotel_name} is confirmed.\n"
        f"Check-in: {check_in_date}\n"
        f"Check-out: {check_out_date}\n\n"
        "Thank you for using Travel App!"
    )

    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
            <div style="background-color: white; padding: 20px; border-radius: 8px; max-width: 520px; margin: 0 auto;">
                <h2 style="color: #1f1f1f; margin-bottom: 16px;">Booking Confirmed!</h2>
                <p style="color: #444;">Dear {safe_name},</p>
                <p style="color: #444;">Your booking at <strong>{hotel_name}</strong> is confirmed.</p>
                <div style="margin: 16px 0; padding: 12px; background: #fafafa; border-radius: 8px;">
                    <p style="margin: 0; color: #333;"><strong>Check-in:</strong> {check_in_date}</p>
                    <p style="margin: 6px 0 0; color: #333;"><strong>Check-out:</strong> {check_out_date}</p>
                </div>
                <p style="color: #666;">Thank you for using Travel App!</p>
            </div>
        </body>
    </html>
    """

    try:
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = BREVO_API_KEY
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to_email}],
            sender={"email": SENDER_EMAIL, "name": SENDER_NAME},
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )

        response = api_instance.send_transac_email(send_smtp_email)
        
        message_id = getattr(response, 'message_id', 'N/A')
        print("\n" + "="*80)
        print(f"[SUCCESS] ✓ Booking confirmation email sent!")
        print(f"[SUCCESS] Message ID: {message_id}")
        print(f"[SUCCESS] To: {to_email}")
        print(f"[SUCCESS] Dates: {check_in_date} → {check_out_date}")
        print("="*80 + "\n")
        
        logger.info(f"[SUCCESS] Booking confirmation email sent. Message ID: {message_id}")
        return True

    except ApiException as e:
        error_details = {
            "status": getattr(e, 'status', 'unknown'),
            "reason": getattr(e, 'reason', 'unknown'),
            "body": getattr(e, 'body', 'unknown')
        }
        print("\n" + "="*80)
        print(f"[BREVO API ERROR] Failed to send booking confirmation email")
        print(f"[BREVO API ERROR] Status Code: {error_details['status']}")
        print(f"[BREVO API ERROR] Reason: {error_details['reason']}")
        print("="*80 + "\n")
        
        logger.error("Brevo API error sending booking confirmation")
        logger.error(f"  Status: {error_details['status']}")
        logger.error(f"  Reason: {error_details['reason']}")
        return False

    except Exception as e:
        print("\n" + "="*80)
        print(f"[ERROR] Failed to send booking confirmation: {type(e).__name__}: {e}")
        print("="*80 + "\n")
        logger.error(f"Error sending booking confirmation: {type(e).__name__}: {e}", exc_info=True)
        return False