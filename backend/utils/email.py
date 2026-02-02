import os
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

    Returns True if successfully submitted to Brevo.
    Returns False and logs errors if Brevo rejects or API fails.
    """
    # DIAGNOSTIC STEP 1: CONFIRM FUNCTION EXECUTION
    print("\n" + "="*80)
    print(f"[DIAGNOSTIC] Email function STARTED")
    print(f"[DIAGNOSTIC] Thread ID: {threading.current_thread().ident}")
    print(f"[DIAGNOSTIC] Thread Name: {threading.current_thread().name}")
    print(f"[DIAGNOSTIC] Is Main Thread: {threading.current_thread() == threading.main_thread()}")
    print(f"[DIAGNOSTIC] Target: {to_email}")
    print(f"[DIAGNOSTIC] Hotel: {hotel_name}")
    print(f"[DIAGNOSTIC] Check-in: {check_in_date}")
    print(f"[DIAGNOSTIC] Check-out: {check_out_date}")
    print(f"[DIAGNOSTIC] User: {user_name}")
    print("="*80 + "\n")
    
    logger.info(f"[DIAGNOSTIC] Email function STARTED for {to_email}")

    # DIAGNOSTIC STEP 2: ENVIRONMENT VALIDATION
    print(f"[ENV CHECK] BREVO_API_KEY present: {bool(BREVO_API_KEY)}")
    print(f"[ENV CHECK] BREVO_API_KEY length: {len(BREVO_API_KEY) if BREVO_API_KEY else 0}")
    print(f"[ENV CHECK] SENDER_EMAIL: {SENDER_EMAIL}")
    print(f"[ENV CHECK] SENDER_NAME: {SENDER_NAME}")
    print(f"[ENV CHECK] DEV_MODE: {DEV_MODE}")
    
    if not BREVO_API_KEY:
        error_msg = "BREVO_API_KEY environment variable not set"
        logger.error(error_msg)
        print(f"[CRITICAL ERROR] {error_msg}")
        if DEV_MODE:
            raise ValueError(error_msg)
        return False

    if not SENDER_EMAIL:
        error_msg = "SENDER_EMAIL environment variable not set"
        logger.error(error_msg)
        print(f"[CRITICAL ERROR] {error_msg}")
        if DEV_MODE:
            raise ValueError(error_msg)
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
        print("[DIAGNOSTIC] Creating Brevo API client...")
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = BREVO_API_KEY
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
        print("[DIAGNOSTIC] Brevo API client created successfully")

        print(f"[DIAGNOSTIC] Building email payload...")
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to_email}],
            sender={"email": SENDER_EMAIL, "name": SENDER_NAME},
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
        print(f"[DIAGNOSTIC] Email payload built - From: {SENDER_EMAIL}, To: {to_email}")

        print("[DIAGNOSTIC] Calling Brevo API send_transac_email()...")
        response = api_instance.send_transac_email(send_smtp_email)
        print("[DIAGNOSTIC] Brevo API call completed")
        
        message_id = getattr(response, 'message_id', 'N/A')
        print("\n" + "="*80)
        print(f"[SUCCESS] ✓ Email sent successfully!")
        print(f"[SUCCESS] Message ID: {message_id}")
        print(f"[SUCCESS] Recipient: {to_email}")
        print(f"[SUCCESS] Full Response: {response}")
        print("="*80 + "\n")
        
        logger.info(f"Booking confirmation email sent: {message_id}")
        logger.info(f"Full Brevo API response: {response}")
        return True

    except ApiException as e:
        error_details = {
            "status": getattr(e, 'status', 'unknown'),
            "reason": getattr(e, 'reason', 'unknown'),
            "body": getattr(e, 'body', 'unknown')
        }
        print("\n" + "="*80)
        print(f"[BREVO API ERROR] Brevo rejected the email request")
        print(f"[BREVO API ERROR] Status Code: {error_details['status']}")
        print(f"[BREVO API ERROR] Reason: {error_details['reason']}")
        print(f"[BREVO API ERROR] Body: {error_details['body']}")
        print("="*80 + "\n")
        
        logger.error("Brevo API exception occurred while sending booking confirmation")
        logger.error(f"  Status code: {error_details['status']}")
        logger.error(f"  Reason: {error_details['reason']}")
        logger.error(f"  Body: {error_details['body']}")
        
        if DEV_MODE:
            raise  # Re-raise in dev mode to surface errors
        return False

    except Exception as e:
        print("\n" + "="*80)
        print(f"[UNEXPECTED ERROR] {type(e).__name__}: {e}")
        print("="*80 + "\n")
        logger.error(f"Unexpected error sending booking confirmation: {type(e).__name__}: {e}", exc_info=True)
        
        if DEV_MODE:
            raise  # Re-raise in dev mode to surface errors
        return False