from datetime import datetime
from email.message import EmailMessage
import smtplib
import ssl
from typing import Protocol

from modules.auth.domain.errors import EmailDeliveryError


class EmailSender(Protocol):
    def send_invite(self, email: str, link: str, expires_at: datetime) -> None: ...


class SMTPEmailSender:
    def __init__(self, host: str, port: int, sender: str, username: str | None = None,
                 password: str | None = None, use_tls: bool = False):
        self._host = host
        self._port = port
        self._sender = sender
        self._username = username
        self._password = password
        self._use_tls = use_tls

    def send_invite(self, email: str, link: str, expires_at: datetime) -> None:
        if not self._sender.strip():
            raise EmailDeliveryError("Configure o remetente SMTP antes de enviar convites")
        if bool(self._username) != bool(self._password):
            raise EmailDeliveryError("Configure usuário e senha SMTP juntos")

        message = EmailMessage()
        message["Subject"] = "Seu convite para o GrafoNet"
        message["From"] = self._sender
        message["To"] = email
        message.set_content(
            f"Você recebeu um convite para o GrafoNet.\n\n{link}\n\n"
            f"O convite vale por sete dias, até {expires_at.isoformat()}.\n"
            "Ele será consumido somente após concluir o cadastro.\n"
        )
        try:
            with smtplib.SMTP(self._host, self._port, timeout=10) as smtp:
                if self._use_tls:
                    smtp.starttls(context=ssl.create_default_context())
                if self._username:
                    smtp.login(self._username, self._password or "")
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException):
            raise EmailDeliveryError("Não foi possível enviar o convite") from None
