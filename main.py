"""Main entrypoint for this application"""
import json
import time
import logging
import warnings
from threading import Lock

from pyduro.actions import (
    get as pyduro_get,
    set as pyduro_set,
    raw as pyduro_raw,
    STATUS_PARAMS,
    SETTINGS,
    CONSUMPTION_DATA,
)
from environs import Env
from paho.mqtt.client import Client as MQTT

# Reading config from environment variables
env = Env()

MQTT_BROKER_HOST = env("MQTT_BROKER_HOST")
MQTT_BROKER_PORT = env.int("MQTT_BROKER_PORT", 1883)
MQTT_CLIENT_ID = env("MQTT_CLIENT_ID", None)
MQTT_USER = env("MQTT_USER", None)
MQTT_PASSWORD = env("MQTT_PASSWORD", None)
MQTT_BASE_TOPIC = env("MQTT_BASE_TOPIC", "aduro2mqtt")

ADURO_HOST = env("ADURO_HOST")
ADURO_SERIAL = env("ADURO_SERIAL")
ADURO_PIN = env("ADURO_PIN")
ADURO_POLL_INTERVAL = env.int("ADURO_POLL_INTERVAL", 30)

LOG_LEVEL = env.log_level("LOG_LEVEL", logging.WARNING)

# Setup logger
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s", level=LOG_LEVEL
)
logging.captureWarnings(True)
warnings.filterwarnings("once")
LOGGER = logging.getLogger("aduro2mqtt")

# Create mqtt client and confiure it according to configuration
mq = MQTT(client_id=MQTT_CLIENT_ID)
mq.username_pw_set(MQTT_USER, MQTT_PASSWORD)

mq.enable_logger(logging.getLogger("aduro2mqtt.mqtt"))

# Pyduro is NOT Thread-safe, we need to handle this explicitly
PYDURO_LOCK = Lock()


@mq.connect_callback()
def _on_connect(
    client, userdata, flags, reason_code, props=None
):  # pylint: disable=unused-argument
    """Subscribe on connect"""
    if reason_code != 0:
        LOGGER.error(
            "Connection failed to %s with reason code: %s", client, reason_code
        )
        return

    client.subscribe(f"{MQTT_BASE_TOPIC}/set")


@mq.disconnect_callback()
def _on_disconnect(
    client, userdata, reason_code, props=None
):  # pylint: disable=unused-argument
    """Subscribe on connect"""
    if reason_code != 0:
        LOGGER.error("Disconnected from %s with reason code: %s", client, reason_code)


@mq.message_callback()
def _handler(client, userdata, message):  # pylint: disable=unused-argument
    """Push each received mqtt message down the processig pipe"""
    LOGGER.debug(
        "Received mqtt message on topic %s with payload %s",
        message.topic,
        message.payload,
    )

    try:
        command = json.loads(message.payload)
        path, value = command["path"], command["value"]
    except json.JSONDecodeError:
        LOGGER.exception(
            "Failed to decode payload %s on topic %s", message.payload, message.topic
        )
        return
    except KeyError:
        LOGGER.exception("Malformed command: %s", command)
        return

    # pylint: disable=redefined-outer-name
    with PYDURO_LOCK:
        if response := pyduro_set.run(ADURO_HOST, ADURO_SERIAL, ADURO_PIN, path, value):
            payload = response.parse_payload()
            LOGGER.debug("Received response with payload: %s", payload)
            if response.status:
                LOGGER.error(
                    "Received non-zero status code from burner: %d", response.status
                )


# Connect to broker
LOGGER.info("Connecting to MQTT broker %s %d", MQTT_BROKER_HOST, MQTT_BROKER_PORT)

# Connect!
mq.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT)

LOGGER.info("Starting background mqtt thread...")
mq.loop_start()


def _try_floatify_values(dikt: dict):  # pylint: disable=redefined-outer-name
    # pylint: disable=invalid-name
    for k, v in dikt.items():
        try:
            dikt[k] = float(v)
        except ValueError:
            pass


# Now, continuously poll the Aduro pellet burner for data and publish to the mqtt broker
while True:
    t0 = time.time()
    # status '*'
    try:
        with PYDURO_LOCK:
            if response := pyduro_raw.run(
                burner_address=ADURO_HOST,
                serial=ADURO_SERIAL,
                pin_code=ADURO_PIN,
                function_id=11,
                payload="*",
            ):
                status = response.parse_payload().split(",")
                dikt = {key: status[ix] for ix, key in enumerate(STATUS_PARAMS.keys())}
                _try_floatify_values(dikt)
                mq.publish(
                    f"{MQTT_BASE_TOPIC}/status", json.dumps(dikt, sort_keys=True)
                )

            else:
                LOGGER.error("response was None from query: 'status'")
    except Exception:  # pylint: disable=broad-exception-caught
        LOGGER.exception("Function 'status' failed!")

    # get 'settings'
    for setting in SETTINGS:
        try:
            with PYDURO_LOCK:
                if response := pyduro_get.run(
                    burner_address=ADURO_HOST,
                    serial=ADURO_SERIAL,
                    pin_code=ADURO_PIN,
                    function_name="settings",
                    path=f"{setting}.*",
                ):
                    dikt = response.parse_payload()
                    _try_floatify_values(dikt)
                    mq.publish(
                        f"{MQTT_BASE_TOPIC}/settings/{setting}",
                        json.dumps(dikt, sort_keys=True),
                    )

        except Exception:  # pylint: disable=broad-exception-caught
            LOGGER.exception("Function: 'settings', path: %s", setting)

    # get 'operating'
    try:
        with PYDURO_LOCK:
            if response := pyduro_get.run(
                burner_address=ADURO_HOST,
                serial=ADURO_SERIAL,
                pin_code=ADURO_PIN,
                function_name="operating",
                path="*",
            ):
                dikt = response.parse_payload()
                _try_floatify_values(dikt)
                mq.publish(
                    f"{MQTT_BASE_TOPIC}/operating", json.dumps(dikt, sort_keys=True)
                )

    except Exception:  # pylint: disable=broad-exception-caught
        LOGGER.exception("Function: 'operating', path: '*'")

    # get 'advanced'
    try:
        with PYDURO_LOCK:
            if response := pyduro_get.run(
                burner_address=ADURO_HOST,
                serial=ADURO_SERIAL,
                pin_code=ADURO_PIN,
                function_name="advanced",
                path="*",
            ):
                dikt = response.parse_payload()
                _try_floatify_values(dikt)
                mq.publish(
                    f"{MQTT_BASE_TOPIC}/advanced", json.dumps(dikt, sort_keys=True)
                )

    except Exception:  # pylint: disable=broad-exception-caught
        LOGGER.exception("Function: 'advanced', path: ''")

    # get 'consumption'
    for key in CONSUMPTION_DATA:
        try:
            with PYDURO_LOCK:
                if response := pyduro_get.run(
                    burner_address=ADURO_HOST,
                    serial=ADURO_SERIAL,
                    pin_code=ADURO_PIN,
                    function_name="consumption",
                    path=key,
                ):
                    data = response.parse_payload().split("=")[-1].split(",")
                    data = [float(value) for value in data]
                    mq.publish(
                        f"{MQTT_BASE_TOPIC}/consumption/{key}",
                        json.dumps(data, sort_keys=True),
                    )

        except Exception:  # pylint: disable=broad-exception-caught
            LOGGER.exception("Function: 'settings', path: %s", key)

    # get 'logs'
    try:
        with PYDURO_LOCK:
            if response := pyduro_get.run(
                burner_address=ADURO_HOST,
                serial=ADURO_SERIAL,
                pin_code=ADURO_PIN,
                function_name="logs",
                path="",
            ):
                dikt = response.parse_payload()
                mq.publish(f"{MQTT_BASE_TOPIC}/logs", json.dumps(dikt, sort_keys=True))

    except Exception:  # pylint: disable=broad-exception-caught
        LOGGER.exception("Function: 'logs', path: ''")

    duration = time.time() - t0
    remainder = ADURO_POLL_INTERVAL - duration

    if remainder > 0:
        time.sleep(remainder)
    else:
        LOGGER.warning(
            "Configured poll interval is shorter than the duration of a single polling event!"
            "Total duration of the last polling event was %d seconds.",
            duration,
        )
