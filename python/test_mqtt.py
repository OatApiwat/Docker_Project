import paho.mqtt.publish as publish
import json
import time
import random

# ตั้งค่า MQTT Broker และ Topic
MQTT_BROKER = "localhost"  # เปลี่ยนเป็น Broker ของคุณ
MQTT_TOPIC = "sensor/data"
i=0
def publish_sensor_data():
    global i
    """ ฟังก์ชันส่งข้อมูล Sensor ไปยัง MQTT Broker ทุก 2 วินาที """
    while True:
        i=i+1
        # สร้างข้อมูลเซ็นเซอร์แบบสุ่ม
        data = {
            "sensor_id": "002",
            "location": "chiangmai",
            "temperature": i,
            "humidity": round(random.uniform(60, 80), 2),
            "pressure": round(random.uniform(1005, 1015), 2)
        }

        # ส่งข้อมูลไปยัง MQTT Broker
        publish.single(MQTT_TOPIC, json.dumps(data), hostname=MQTT_BROKER, port=1883)
        print(f"📤 Data sent: {data}")

        # รอ 2 วินาทีก่อนส่งข้อมูลใหม่
        time.sleep(2)

# ตรวจสอบว่าถูกเรียกใช้งานเป็น Script หลัก
if __name__ == "__main__":
    publish_sensor_data()
