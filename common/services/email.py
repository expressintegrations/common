import smtplib
from email.message import EmailMessage

from common.services.base import BaseService


class EmailService(BaseService):

    def __init__(
        self,
        sender: str,
        password: str
    ) -> None:
        self.sender = sender
        self.password = password
        super().__init__(log_name="email.service")

    def send_email(self, recipient, subject, message) -> None:
        msg = EmailMessage()
        msg.set_payload(str(message))
        msg['Subject'] = subject
        msg['From'] = self.sender
        msg['To'] = recipient
        msg.add_header('Content-Type', 'text/html')

        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(self.sender, self.password)
        server.send_message(msg)
        server.quit()
