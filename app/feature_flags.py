# app/feature_flags.py
import os
import logging

import ldclient
from ldclient import Context
from ldclient.config import Config

ld_client = None  # cliente global reutilizable


def init_launchdarkly():
    """
    Inicializa el cliente de LaunchDarkly.
    Debe llamarse UNA vez al arrancar la app (en create_app()).
    """
    global ld_client

    sdk_key = os.getenv("LD_SDK_KEY")
    if not sdk_key:
        logging.warning(
            "LaunchDarkly: LD_SDK_KEY no configurada, los feature flags devolverán False"
        )
        ld_client = None
        return

    ldclient.set_config(Config(sdk_key))
    ld_client = ldclient.get()

    if not ld_client.is_initialized():
        logging.error("LaunchDarkly no se inicializó correctamente")
    else:
        logging.info("LaunchDarkly inicializado correctamente")


def is_feature_enabled(flag_key: str, user_key: str = "anonymous") -> bool:
    """
    Devuelve True/False según el estado del flag para un usuario dado.
    """
    if ld_client is None:
        return False

    # Contexto igual al ejemplo de LaunchDarkly
    context = (
        Context.builder(user_key)
        .kind("user")
        .build()
    )

    # Tercer parámetro: valor por defecto si falla algo
    return ld_client.variation(flag_key, context, False)
