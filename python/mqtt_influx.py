import json
import paho.mqtt.client as mqtt
from influxdb import InfluxDBClient

# 1️⃣ กำหนดค่า MQTT Broker และ Topic
MQTT_BROKER = "localhost"  # เปลี่ยนเป็น MQTT Broker ของคุณ
MQTT_PORT = 1883
MQTT_TOPIC = "sensor/data"

# 2️⃣ กำหนดค่า InfluxDB
INFLUXDB_HOST = "localhost"  # หรือ IP ของ InfluxDB
INFLUXDB_PORT = 8086
INFLUXDB_DBNAME = "sensor_db"
INFLUXDB_USER = "admin"  # ถ้ามี Authentication
INFLUXDB_PASSWORD = "adminpassword"

# 3️⃣ ฟังก์ชันเชื่อมต่อกับ InfluxDB
def connect_influxdb():
    client = InfluxDBClient(INFLUXDB_HOST, INFLUXDB_PORT, INFLUXDB_USER, INFLUXDB_PASSWORD, INFLUXDB_DBNAME)

    # ตรวจสอบว่า Database มีอยู่แล้วหรือไม่ ถ้าไม่มีให้สร้าง
    databases = client.get_list_database()
    if INFLUXDB_DBNAME not in [db['name'] for db in databases]:
        client.create_database(INFLUXDB_DBNAME)
        print(f"✅ Created database: {INFLUXDB_DBNAME}")

    return client

# 4️⃣ ฟังก์ชันจัดการข้อมูลที่ได้รับจาก MQTT
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        print(f"📩 Received data: {payload}")

        json_body = [
            {
                "measurement": "sensor_data",
                "tags": {
                    "sensor_id": payload.get("sensor_id", "unknown"),
                    "location": payload.get("location", "unknown"),
                },
                "fields": {
                    "temperature": float(payload["temperature"]),
                    "humidity": float(payload["humidity"]),
                    "pressure": float(payload["pressure"]),
                }
            }
        ]

        client_influx.write_points(json_body)
        print("✅ Data written to InfluxDB")

    except Exception as e:
        print(f"❌ Error: {e}")

# 5️⃣ ฟังก์ชันเริ่มต้น MQTT Client
def start_mqtt():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT)
    client.subscribe(MQTT_TOPIC)
    print(f"📡 Listening for messages on topic: {MQTT_TOPIC}")
    client.loop_forever()

# 6️⃣ ตรวจสอบว่าโค้ดนี้รันเป็นสคริปต์หลักหรือไม่
if __name__ == "__main__":
    client_influx = connect_influxdb()  # เชื่อมต่อกับ InfluxDB
    start_mqtt()  # เริ่มรับข้อมูลจาก MQTT
