from datetime import datetime, timezone
from email.message import EmailMessage
import smtplib
from unittest.mock import Mock, patch

import pytest

from modules.auth.domain.errors import EmailDeliveryError
from modules.auth.email import SMTPEmailSender


def test_smtp_sender_uses_starttls_authentication_and_text_message():
    sender = SMTPEmailSender(
        "smtp.sendgrid.net", 587, "sender@example.org", "apikey", "sendgrid-api-key", True,
    )
    expires_at = datetime(2026, 11, 6, tzinfo=timezone.utc)
    with patch("modules.auth.email.smtplib.SMTP") as smtp_factory:
        smtp = Mock()
        smtp_factory.return_value.__enter__.return_value = smtp

        sender.send_invite("recipient@insper.edu.br", "https://example.org/register?token=test", expires_at)

    smtp_factory.assert_called_once_with("smtp.sendgrid.net", 587, timeout=10)
    smtp.starttls.assert_called_once()
    smtp.login.assert_called_once_with("apikey", "sendgrid-api-key")
    message = smtp.send_message.call_args.args[0]
    assert isinstance(message, EmailMessage)
    assert message["From"] == "sender@example.org"
    assert message["To"] == "recipient@insper.edu.br"
    assert "https://example.org/register?token=test" in message.get_content()
    assert expires_at.isoformat() in message.get_content()


@pytest.mark.parametrize(
    ("sender_address", "username", "password"),
    [
        ("", "smtp-user", "smtp-password"),
        ("sender@example.org", "smtp-user", None),
        ("sender@example.org", None, "smtp-password"),
    ],
)
def test_smtp_sender_rejects_missing_sender_or_incomplete_credentials(sender_address, username, password):
    sender = SMTPEmailSender("smtp.sendgrid.net", 587, sender_address, username, password, True)

    with patch("modules.auth.email.smtplib.SMTP") as smtp_factory:
        with pytest.raises(EmailDeliveryError):
            sender.send_invite("recipient@insper.edu.br", "https://example.org/invite", datetime.now(timezone.utc))

    smtp_factory.assert_not_called()


def test_smtp_sender_hides_transport_errors():
    sender = SMTPEmailSender("smtp.sendgrid.net", 587, "sender@example.org", "apikey", "sendgrid-api-key", True)
    with patch("modules.auth.email.smtplib.SMTP", side_effect=smtplib.SMTPException("sensitive server detail")):
        with pytest.raises(EmailDeliveryError, match="Não foi possível enviar o convite") as error:
            sender.send_invite("recipient@insper.edu.br", "https://example.org/invite", datetime.now(timezone.utc))

    assert "sensitive server detail" not in str(error.value)
