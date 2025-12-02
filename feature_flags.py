# app/feature_flags.py
import os
import logging
import launchdarkly_server_sdk as ldclient
from launchdarkly_server_sdk.config import Config

LD_SDK_KEY = os.getenv("LD_SDK_KEY")

ld_client = None

def init_launchdarkly():
    """
    Inicializa el cliente de LaunchDarkly.
    Llamar UNA vez al arrancar la app (por ejemplo en create_app()).
    """
    global ld_client
    if not LD_SDK_KEY:
        logging.warning("LaunchDarkly: LD_SDK_KEY no configurada, los flags devolverán False")
        return

    ld_client = ldclient.LDClient(Config(sdk_key=LD_SDK_KEY))
    logging.info("LaunchDarkly inicializado correctamente")


def is_feature_enabled(flag_key: str, user_key: str = "anonymous") -> bool:
    """
    Devuelve True/False según el estado del flag.
    """
    if not ld_client:
        return False

    user = {"key": user_key}
    return ld_client.variation(flag_key, user, False)
