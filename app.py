import paho.mqtt.client as mqtt
import redis
import json
import logging
from decouple import config

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] (%(threadName)-10s) %(message)s')

# get config items
redis_host = config("REDIS_HOST")
redis_password = config("REDIS_PASSWORD")
mqtt_broker_host = config("MQTT_BROKER_HOST")
mqtt_hidreader_topic_pattern = config("MQTT_HIDREADER_TOPIC_PATTERN")
mqtt_door_topic_pattern = config("MQTT_DOOR_TOPIC_PATTERN")

# connect to redis
redis_client = redis.Redis(host=redis_host, port=6379, db=0, password=redis_password)

# define mqtt client
client = mqtt.Client()

def on_publish(client, userdata, result):
  logging.info("Data published to topic with result code {rc}".format(rc=str(result)))

def on_connect(client, userdata, flags, rc):
  logging.info("Connected to MQTT broker, subscribing to {topic}...".format(topic=mqtt_hidreader_topic_pattern))
  client.subscribe(mqtt_hidreader_topic_pattern)

def on_message(client, userdata, msg):
  logging.info("Got a message from {topic}".format(topic=msg.topic))
  payload = msg.payload.decode("utf-8")
  logging.info("Payload = {payload}".format(payload=msg.payload))
  payload = json.loads(payload)
  logging.info("Processing message...")
  process_message(payload)

def process_message(payload):
  logging.info("Starting to process message...")
  lookup_name = "access/{door}/{fc}/{cc}".format(door=payload["door_name"], fc=payload["facility_code"], cc=payload["card_code"])
  logging.info("Checking for '{key}' in redis".format(key=lookup_name))
  result = redis_client.get(lookup_name)
  logging.info("Got result from redis: {res}".format(res=result))
  if result:
    result = result.decode("utf-8")
    if result == "yes":
      logging.info("Door access is allowed")
      client.publish(mqtt_door_topic_pattern.format(door=payload["door_name"]), "open")
    else:
      logging.info("Door access is not allowed")
  else:
    logging.info("Door access is not defined, so assuming it is not allowed")

# main method to run programme
def run():
  client.on_connect = on_connect
  client.on_message = on_message
  client.on_publish = on_publish
  client.connect(mqtt_broker_host)
  client.loop_forever()

if __name__ == "__main__":
  run()
