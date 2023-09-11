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

## Integration to Home Assistant
`aduro2mqtt` does not provide logic to take part in MQTT Discovery (https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery) and, therefore, integration towards Home Assistant must be done through manual setup of mqtt sensors and switches. A basic example of a yaml configuration is shown below.

```yaml
mqtt:
  sensor:
  - name: "Aduro H2 Smoke temperature"
    state_topic: "aduro2mqtt/status"
    value_template: "{{ value_json.smoke_temp }}"
    unit_of_measurement: "°C"
  - name: "Aduro H2 Shaft temperature"
    state_topic: "aduro2mqtt/status"
    value_template: "{{ value_json.shaft_temp }}"
    unit_of_measurement: "°C"
  - name: "Aduro H2 Total hours"
    state_topic: "aduro2mqtt/consumption/counter"
    value_template: "{{ value_json[0] }}"
    unit_of_measurement: "h"
  - name: "Aduro H2 Room temperature"
    state_topic: "aduro2mqtt/status"
    value_template: "{{ value_json.boiler_temp }}"
    unit_of_measurement: "°C"
  
  switch:
  - name: "Aduro H2 toggle"
    command_topic: "aduro2mqtt/set"
    payload_on: '{"path": "misc.start", "value": "1"}'
    payload_off: '{"path": "misc.stop", "value": "1"}'
  
  select:
  - name: "Aduro H2 Fixed power (%)"
    command_topic: "aduro2mqtt/set"
    options:
      - "10"
      - "50"
      - "100"
    command_template: '{"path": "regulation.fixed_power", "value": {{ value}} }'
    state_topic: "aduro2mqtt/settings/regulation"
    value_template: "{{ value_json.fixed_power | int }}"
```
