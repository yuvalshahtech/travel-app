# Set Brevo environment variables for the current session

# REQUIRED: Set your Brevo API key here
$env:BREVO_API_KEY = "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"
# OPTIONAL: Customize sender details (must be verified in Brevo dashboard)
$env:SENDER_EMAIL = "yuvalshahtech@gmail.com"
$env:SENDER_NAME = "Travel-App"

# OPTIONAL: Enable dev mode to log OTP in console instead of sending email
# Uncomment the line below for development:
# $env:DEV_MODE = "true"

Write-Host "✅ Environment variables set!" -ForegroundColor Green
Write-Host "BREVO_API_KEY: SET" -ForegroundColor Cyan
Write-Host "SENDER_EMAIL: $env:SENDER_EMAIL" -ForegroundColor Cyan
Write-Host "SENDER_NAME: $env:SENDER_NAME" -ForegroundColor Cyan
Write-Host "DEV_MODE: $env:DEV_MODE" -ForegroundColor Cyan
Write-Host "`nNow run: python main.py" -ForegroundColor Yellow
