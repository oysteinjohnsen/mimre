"""Sending email (login codes)."""

import smtplib
from email.message import EmailMessage
from typing import Literal, Protocol

from app.config import settings

Language = Literal["nb", "en"]


class Mailer(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...


class SmtpMailer:
    def send(self, to: str, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["From"] = settings.mail_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)

        smtp_class = smtplib.SMTP_SSL if settings.smtp_ssl else smtplib.SMTP
        with smtp_class(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            if settings.smtp_starttls:
                smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password or "")
            smtp.send_message(msg)


def get_mailer() -> Mailer:
    """FastAPI dependency (replaced by a fake in tests)."""
    return SmtpMailer()


def login_code_email(code: str, language: Language, minutes: int) -> tuple[str, str]:
    """(subject, body). The code is in the subject so phones can offer to fill it in."""
    if language == "en":
        return (
            f"{code} is your Mimre login code",
            f"Your code for logging in to Mimre is: {code}\n\n"
            f"It is valid for {minutes} minutes.\n\n"
            "If you didn't try to log in, you can ignore this email – but consider changing your "
            "password, since someone else appears to know it.\n",
        )
    return (
        f"{code} er koden din for Mimre",
        f"Koden for å logge inn i Mimre er: {code}\n\n"
        f"Den er gyldig i {minutes} minutter.\n\n"
        "Hvis du ikke prøvde å logge inn, kan du se bort fra denne e-posten – men vurder å bytte "
        "passord, siden noen andre ser ut til å kjenne det.\n",
    )
