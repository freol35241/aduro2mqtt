# aduro2mqtt
A microservice that acts as a bridge between an Aduro pellet burner (using the NBE udp protocol) and an mqtt broker.

Available as a docker image, docker-compose exampe below:

```yaml
version: "3.9"
services:
  aduro2mqtt:
    image: ghcr.io/freol35241/aduro2mqtt
    restart: unless-stopped
    environment:
      - MQTT_BROKER_HOST=<ip of mqtt broker>
      - ADURO_HOST=<ip of aduro pellet burner>
      - ADURO_SERIAL=<serial number of aduro pellet burner>
      - ADURO_PIN=<pin code for aduro pellet burner>
```

Avilable configuration options:

```
MQTT_BROKER_HOST
    Hostname/ip of mqtt broker to connect to. Required.

MQTT_BROKER_PORT
    Port number of mqtt broker to connect to. Optional, defaults to 1883.

MQTT_CLIENT_ID
    Client id to use when connecting to mqtt broker. Optional, defaults to None.

MQTT_USER
    Username to use when connecting to mqtt broker. Optional, defaults to None.

MQTT_PASSWORD
    Password to use when connecting to mqtt broker. Optional, defaults to None.

MQTT_BASE_TOPIC
    Base topic which is used to prefix all publish and subscribe topics of this service. Optional, defaults to aduro2mqtt.

ADURO_HOST
    IP address of Aduro pellet burner to connect to. Required.

ADURO_SERIAL
    Serial number of the Aduro pellet burner to connect to. Required.

ADURO_PIN
    Pin code to use when connecting to the Aduro pellet burner. Required.

ADURO_POLL_INTERVAL
    Interval to use when polling data from the Aduro peller burner. Optional, defaults to 30s.

LOG_LEVEL
    Logging level of the application. Optional, defaults to WARNING.
```