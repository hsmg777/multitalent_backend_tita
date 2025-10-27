import smtplib, ssl
from email.message import EmailMessage
from flask import current_app

def send_mail(to: str, subject: str, html: str, inline_images: dict | None = None):
    server = current_app.config.get("MAIL_SERVER")
    if not server:
        current_app.logger.warning("MAIL_SERVER no configurado. Render del mail:\n%s", html)
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = current_app.config["MAIL_SENDER"]
    msg["To"] = to
    msg.set_content("Este email requiere un cliente que soporte HTML.")
    msg.add_alternative(html, subtype="html")

   
    if inline_images:
        html_part = msg.get_body(preferencelist=("html",))
        for cid, (mimetype, data) in inline_images.items():
            if not data:
                continue
            maintype, subtype = mimetype.split("/", 1)
            html_part.add_related(data, maintype=maintype, subtype=subtype, cid=cid)

    port = current_app.config["MAIL_PORT"]
    username = current_app.config["MAIL_USERNAME"]
    password = current_app.config["MAIL_PASSWORD"]
    use_tls = current_app.config["MAIL_USE_TLS"]

    context = ssl.create_default_context()
    with smtplib.SMTP(server, port) as smtp:
        if use_tls:
            smtp.starttls(context=context)
        if username and password:
            smtp.login(username, password)
        smtp.send_message(msg)
