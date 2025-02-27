import asyncio
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

async def send_test_email():
    message = MIMEMultipart()
    message['From'] = "dimacheban23@meta.ua"
    message['To'] = "dimacheban23@meta.ua"
    message['Subject'] = "Test Email"
    message.attach(MIMEText("This is a test email.", 'plain'))

    try:
        async with aiosmtplib.SMTP(
            hostname="smtp.meta.ua", 
            port=465, 
            use_tls=True,
            timeout=10
        ) as smtp:
            await smtp.login("dimacheban23@meta.ua", "Saksaganskogo22")
            await smtp.send_message(message)
            print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {str(e)}")

if __name__ == "__main__":
    asyncio.run(send_test_email())