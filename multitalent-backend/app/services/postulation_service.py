# app/services/postulation_service.py
from datetime import datetime
from typing import Optional
from flask import current_app
from ..ext.db import db
from ..ext.mail import send_mail
from ..models.web_portal.postulation import Postulation
from ..models.admin.vacancy import Vacancy  
import os


try:
    from ..realtime import socketio
except ImportError:
    socketio = None

VALID_STATES = {
    "submitted",
    "accepted",
    "prescreen_call",
    "personality_test_ready",
    "interview_scheduled",
    "selection_pending",
    "hired",
    "rejected",
}


def _candidate_portal_url(postulation: Postulation) -> str:
    """
    Devuelve SIEMPRE una URL ABSOLUTA al panel del candidato.
    Cambiamos a /my-applications (lista) en lugar de la ruta por id.
    """
    base = (
        current_app.config.get("FRONTEND_URL")
    )
    return f"{base.rstrip('/')}/my-applications"



def _mail_accepted(postulation: Postulation) -> Optional[str]:
    """Envía correo de aceptación y devuelve destinatario (o None)."""
    applicant = getattr(postulation, "applicant", None)
    to = (getattr(applicant, "email", "") or "").strip()
    if not to:
        current_app.logger.warning(
            "[MAIL] Postulation %s sin email de applicant; se omite envío.",
            postulation.id,
        )
        return None

    subject = "¡Has sido seleccionado para continuar el proceso!"
    cta = _candidate_portal_url(postulation)
    nombre = (getattr(applicant, "nombre", "") or "Postulante").strip()

    LOGO_CID = "logo_mp"
    candidate_paths = [
        "/app/app/assets/mail/logo-multi.png",
        "/app/assets/mail/logo-multi.png",
        os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets", "mail", "logo-multi.png")),
    ]
    logo_bytes = None
    for p in candidate_paths:
        try:
            with open(p, "rb") as f:
                logo_bytes = f.read()
                current_app.logger.info("[MAIL] Logo inline desde: %s", p)
                break
        except Exception:
            continue

    if logo_bytes:
        logo_img_tag = (
            f'<img src="cid:{LOGO_CID}" width="40" height="40" alt="Multiapoyo" '
            'style="display:block;border:0;outline:none;text-decoration:none;'
            '-ms-interpolation-mode:bicubic;">'
        )
    else:
        current_app.logger.warning("[MAIL] Logo inline NO encontrado, usando remoto.")
        logo_img_tag = (
            '<img src="https://clientes.multiapoyo.com.ec/assets/logo-square.3d15754b.png" '
            'width="40" height="40" alt="Multiapoyo" '
            'style="display:block;border:0;outline:none;text-decoration:none;'
            '-ms-interpolation-mode:bicubic;">'
        )

    # ---- Botón bulletproof (VML Outlook) ----
    button_html = f"""
      <!--[if mso]>
      <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml"
                   xmlns:w="urn:schemas-microsoft-com:office:word"
                   href="{cta}"
                   style="height:40px;v-text-anchor:middle;width:220px;"
                   arcsize="20%" stroke="f" fillcolor="#E61E5C">
        <w:anchorlock/>
        <center style="color:#ffffff;font-family:Arial,Helvetica,sans-serif;font-size:14px;font-weight:700;">
          Ver mi proceso
        </center>
      </v:roundrect>
      <![endif]-->

      <!--[if !mso]><!-- -->
      <a href="{cta}" target="_blank"
         style="background:#E61E5C;border-radius:10px;display:inline-block;
                padding:12px 22px;font:700 14px Arial,Helvetica,sans-serif;
                color:#ffffff;text-decoration:none;mso-line-height-rule:exactly;">
        Ver mi proceso
      </a>
      <!--<![endif]-->
    """

    html = f"""
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;">
      Accede a tu panel para ver los siguientes pasos del proceso de selección.
    </div>

    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background:#F6F7FB;">
      <tr>
        <td align="center" style="padding:24px;">
          <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="max-width:600px;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
            <tr>
              <td style="background:#ffffff;padding:20px 24px;border-bottom:6px solid #1E2A6B;">
                <table width="100%" role="presentation" cellspacing="0" cellpadding="0" border="0" style="mso-table-lspace:0pt;mso-table-rspace:0pt;">
                  <tr>
                    <td align="left" style="line-height:0;mso-line-height-rule:exactly;">
                      <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="line-height:0;mso-table-lspace:0pt;mso-table-rspace:0pt;">
                        <tr>
                          <td style="line-height:0;mso-line-height-rule:exactly;">
                            {logo_img_tag}
                          </td>
                        </tr>
                      </table>
                    </td>
                    <td align="right" style="font:500 12px Arial,Helvetica,sans-serif;color:#5B6472;">
                      Notificación de proceso
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <tr>
              <td style="padding:28px 28px 8px 28px;">
                <h1 style="margin:0;font:800 22px Arial,Helvetica,sans-serif;color:#1E2A6B;">
                  ¡Hola {nombre}!
                </h1>
                <p style="margin:0;font:400 14px Arial,Helvetica,sans-serif;color:#2B2B2B;">
                  ¡Buenas noticias! Fuiste <strong style="color:#1E2A6B;">aceptado</strong> para continuar con el proceso de selección en
                  <strong>Multiapoyo</strong>.
                </p>
              </td>
            </tr>

            <tr>
              <td style="padding:8px 28px;">
                <p style="margin:0 0 12px;font:400 14px Arial,Helvetica,sans-serif;color:#2B2B2B;">
                  Desde tu panel podrás ver:
                </p>
                <ul style="margin:0 0 16px 18px;font:400 14px Arial,Helvetica,sans-serif;color:#2B2B2B;">
                  <li>El estado actual de tu postulación</li>
                  <li>Próximos pasos y fechas</li>
                  <li>Documentación o exámenes requeridos</li>
                </ul>
                <p style="margin:0 0 12px;font:400 14px Arial,Helvetica,sans-serif;color:#2B2B2B;">
                    Da click en el botón e inicia sesión, luego da click en el menú ubicado en la parte superior derecha y luego click en "Mis postulaciones"
                </p>

                <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:20px 0 8px;">
                  <tr>
                    <td align="center">
                      {button_html}
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <tr>
              <td style="padding:16px 28px 0;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                  <tr>
                    <td style="border-top:1px solid #E6EAF5;height:1px;font-size:0;line-height:0;">&nbsp;</td>
                  </tr>
                </table>
              </td>
            </tr>

            <tr>
              <td style="padding:16px 28px 24px;">
                <p style="margin:0 0 8px;font:400 12px Arial,Helvetica,sans-serif;color:#5B6472;">
                  Este es un correo automático, por favor no respondas a este mensaje.
                </p>
                <p style="margin:0;font:400 12px Arial,Helvetica,sans-serif;color:#5B6472;">
                  ¿Necesitas ayuda? Escríbenos a
                  <a href="mailto:info@multiapoyo.com.ec" style="color:#E61E5C;">info@multiapoyo.com.ec</a>.
                </p>
              </td>
            </tr>

            <tr>
              <td style="background:#F1F3F8;padding:14px 24px;text-align:center;">
                <p style="margin:6px 0;font:400 11px Arial,Helvetica,sans-serif;color:#5B6472;">
                  © {datetime.utcnow().year} Multiapoyo. Todos los derechos reservados.
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
    """

    inline_images = {LOGO_CID: ("image/png", logo_bytes)} if logo_bytes else None

    current_app.logger.info(
        "[MAIL] Enviando aceptación postulation_id=%s a=%s", postulation.id, to
    )
    send_mail(to=to, subject=subject, html=html, inline_images=inline_images)
    return to


def _emit_postulation_updated(postulation: Postulation) -> None:
    """
    Emite el evento de actualización de postulación de forma SEGURA.
    Nunca accede a relaciones perezosas (postulation.vacancy). Si requiere info
    básica de la vacante, la obtiene con una consulta específica y liviana.
    """
    if not socketio:
        current_app.logger.debug("[SOCKETIO] socketio no disponible; no se emite evento.")
        return

    payload = {
        "id": postulation.id,
        "status": postulation.status,
        "updated_at": postulation.updated_at.isoformat(),
        "vacancy_id": postulation.vacancy_id,
    }

    try:
        vac = (
            db.session.query(
                Vacancy.id,
                Vacancy.title,
                Vacancy.location,
                Vacancy.modality,
            )
            .filter(Vacancy.id == postulation.vacancy_id)
            .first()
        )
        if vac:
            payload["vacancy"] = {
                "id": vac.id,
                "title": vac.title,
                "location": vac.location,
                "modality": vac.modality,
            }
    except Exception as e:
        current_app.logger.warning("[SOCKETIO] No se pudo enriquecer vacancy: %s", e)

    try:
        room = f"user:{postulation.applicant_id}"
        socketio.emit("postulation_updated", payload, room=room)
        current_app.logger.info(
            "[SOCKETIO] Emitido postulation_updated postulation_id=%s room=%s",
            postulation.id,
            room,
        )
    except Exception as e:
        current_app.logger.warning(
            "[SOCKETIO] No se pudo emitir postulation_updated: %s", e
        )


def transition_to(
    postulation: Postulation, new_status: str, *, send_email: bool = True
) -> Postulation:
    """
    Aplica transición de estado. Devuelve Postulation.
    Maneja:
      - Validación de estados
      - Guardado en DB
      - Envío de correo (si aplica)
      - Emisión de evento por socket (si está habilitado)
    """
    if new_status not in VALID_STATES:
        raise ValueError(f"Estado inválido: {new_status}")

    prev = (postulation.status or "").strip().lower()

    allowed_from = {
        "accepted": {"submitted", "", None, "rejected"},
        "prescreen_call": {"accepted"},
        "personality_test_ready": {"prescreen_call"},
        "interview_scheduled": {"personality_test_ready"},
        "selection_pending": {"interview_scheduled"},
        "hired": {"selection_pending"},
        "rejected": {
            "submitted",
            "accepted",
            "prescreen_call",
            "personality_test_ready",
            "interview_scheduled",
            "selection_pending",
        },
    }

    if new_status in allowed_from and prev not in allowed_from[new_status]:
        raise ValueError(f"Transición no permitida: {prev or '∅'} → {new_status}")

    postulation.status = new_status
    postulation.updated_at = datetime.utcnow()

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

    setattr(postulation, "_mail_to", None)
    setattr(postulation, "_mail_sent", False)
    setattr(postulation, "_mail_error", None)

    if send_email and new_status == "accepted":
        try:
            mail_to = _mail_accepted(postulation)
            setattr(postulation, "_mail_to", mail_to)
            setattr(postulation, "_mail_sent", bool(mail_to))
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            setattr(postulation, "_mail_error", err)
            current_app.logger.exception(
                "[MAIL] Error enviando aceptación postulation_id=%s: %s",
                postulation.id,
                err,
            )

    # Emitir evento realtime (seguro)
    _emit_postulation_updated(postulation)

    return postulation
