import smtplib
import logging
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any

logger = logging.getLogger(__name__)

class EmailTool:
    """
    Инструмент для отправки электронных писем с использованием SMTP.
    Поддерживает бесплатные почтовые сервисы (Gmail, Outlook и др.).
    """

    def get_definition(self) -> Dict[str, Any]:
        return {
            "name": "email",
            "description": "Отправка электронных писем по SMTP (SMTP, Gmail, Outlook).",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Email получателя"},
                    "subject": {"type": "string", "description": "Тема письма"},
                    "body": {"type": "string", "description": "Текст сообщения"},
                    "smtp_server": {"type": "string", "description": "Адрес SMTP сервера (default: smtp.gmail.com)"},
                    "smtp_port": {"type": "integer", "description": "Порт SMTP сервера (default: 587)"},
                    "sender_email": {"type": "string", "description": "Email отправителя"},
                    "sender_password": {"type": "string", "description": "Пароль или App Password отправителя"}
                },
                "required": ["to", "subject", "body"]
            }
        }

    async def execute(self, to: str, subject: str, body: str, **kwargs) -> Dict[str, Any]:
        try:
            smtp_server = kwargs.get("smtp_server") or os.environ.get("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = kwargs.get("smtp_port") or int(os.environ.get("SMTP_PORT", 587))
            sender_email = kwargs.get("sender_email") or os.environ.get("SENDER_EMAIL")
            sender_password = kwargs.get("sender_password") or os.environ.get("SENDER_PASSWORD")
            
            if not sender_email or not sender_password:
                return {"success": False, "error": "Email отправителя или пароль не указаны. Настройте переменные окружения SENDER_EMAIL и SENDER_PASSWORD."}
            
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = to
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
            
            return {"success": True, "message": f"Email успешно отправлен на адрес {to}"}
            
        except Exception as e:
            logger.error(f"Ошибка EmailTool: {e}")
            return {"success": False, "error": str(e)}
