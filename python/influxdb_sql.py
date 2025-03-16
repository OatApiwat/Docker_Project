import time
import pandas as pd
from datetime import datetime, timedelta
import pytz
from influxdb import InfluxDBClient
import pymssql

# 🟢 ตั้งค่าการเชื่อมต่อ InfluxDB
INFLUXDB_HOST = "localhost"
INFLUXDB_PORT = 8086
INFLUXDB_DBNAME = "sensor_db"
INFLUXDB_USER = "admin"
INFLUXDB_PASSWORD = "adminpassword"

# 🟢 ตั้งค่าการเชื่อมต่อ MSSQL
MSSQL_HOST = "localhost"
MSSQL_USER = "sa"
MSSQL_PASSWORD = "NewStrong!Passw0rd"
MSSQL_DBNAME = "sensor_db"

# 🟢 ตั้งค่า INTERVAL_TIME (1 นาที - 1 วัน)
INTERVAL_TIME = 1  # นาที

# 🟢 กำหนดโซนเวลาไทย (UTC+7)
BANGKOK_TZ = pytz.timezone("Asia/Bangkok")

# 🟢 ตรวจสอบและสร้างตาราง MSSQL ถ้ายังไม่มี
def create_table():
    conn = pymssql.connect(MSSQL_HOST, MSSQL_USER, MSSQL_PASSWORD, MSSQL_DBNAME)
    cursor = conn.cursor()

    # ตรวจสอบว่าตารางมีอยู่แล้วหรือไม่
    cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'sensor_data'")
    if cursor.fetchone()[0] == 0:
        query = """
        CREATE TABLE sensor_data (
            id INT IDENTITY(1,1) PRIMARY KEY,
            sensor_id VARCHAR(50),
            location VARCHAR(100),
            temperature FLOAT,
            humidity FLOAT,
            pressure FLOAT,
            timestamp DATETIME
        )
        """
        cursor.execute(query)
        conn.commit()
        print("✅ Created table: sensor_data")
    else:
        print("✅ Table sensor_data already exists, skipping creation.")

    conn.close()

# 🟢 ดึงข้อมูลล่าสุดจาก MSSQL
def get_last_timestamp():
    conn = pymssql.connect(MSSQL_HOST, MSSQL_USER, MSSQL_PASSWORD, MSSQL_DBNAME)
    cursor = conn.cursor()

    query = "SELECT MAX(timestamp) FROM sensor_data"
    cursor.execute(query)
    last_timestamp = cursor.fetchone()[0]

    conn.close()
    return last_timestamp

# 🟢 ดึงข้อมูลจาก InfluxDB ตามช่วงเวลา
def fetch_influxdb(start_time, end_time):
    client = InfluxDBClient(INFLUXDB_HOST, INFLUXDB_PORT, INFLUXDB_USER, INFLUXDB_PASSWORD, INFLUXDB_DBNAME)

    # แปลงเวลาเป็น UTC สำหรับ InfluxDB
    start_utc = start_time.astimezone(pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_utc = end_time.astimezone(pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"📡 Fetching data from {start_utc} to {end_utc} (UTC)")

    query = f"SELECT * FROM sensor_data WHERE time >= '{start_utc}' AND time < '{end_utc}'"
    result = client.query(query)

    points = list(result.get_points())
    df = pd.DataFrame(points)

    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], errors="coerce")

        # ตรวจสอบว่ามี timezone หรือไม่
        if df["time"].dt.tz is None:
            df["time"] = df["time"].dt.tz_localize("UTC").dt.tz_convert(BANGKOK_TZ)
        else:
            df["time"] = df["time"].dt.tz_convert(BANGKOK_TZ)

        df.rename(columns={"time": "timestamp"}, inplace=True)
    else:
        print("⚠️ Warning: 'time' column not found, skipping time conversion")

    return df


# 🟢 บันทึกข้อมูลลง MSSQL
def insert_to_mssql(df):
    if df.empty:
        print("⚠️ No new data to insert")
        return
    
    conn = pymssql.connect(MSSQL_HOST, MSSQL_USER, MSSQL_PASSWORD, MSSQL_DBNAME)
    cursor = conn.cursor()

    for _, row in df.iterrows():
        query = """
        INSERT INTO sensor_data (sensor_id, location, temperature, humidity, pressure, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s);
        """
        cursor.execute(query, (row["sensor_id"], row["location"], row["temperature"], row["humidity"], row["pressure"], row["timestamp"]))

    conn.commit()
    conn.close()
    print(f"✅ Inserted {len(df)} records into MSSQL")

# 🟢 ดึงข้อมูลจาก InfluxDB และบันทึกลง MSSQL ทุก INTERVAL_TIME นาที
def run_sync():
    create_table()  # ตรวจสอบและสร้างตารางถ้ายังไม่มี
    last_executed = None  # เวลาที่ทำงานล่าสุด

    while True:
        now = datetime.now(BANGKOK_TZ)
        current_minute = now.minute
        current_second = now.second

        # คำนวณเวลาที่ต้องทำงาน (ต้องเป็นนาทีที่ลงตัวกับ INTERVAL_TIME)
        if current_minute % INTERVAL_TIME == 0 and current_second >= 5:
            if last_executed != now.replace(second=0, microsecond=0):
                start_time = now - timedelta(minutes=INTERVAL_TIME)
                end_time = now
                df = fetch_influxdb(start_time, end_time)  # ดึงข้อมูลจาก InfluxDB
                insert_to_mssql(df)  # บันทึกลง MSSQL
                last_executed = now.replace(second=0, microsecond=0)

        time.sleep(1)  # ตรวจสอบทุกๆ 1 วินาที

# 🟢 เริ่มทำงานถ้าถูกเรียกใช้เป็นสคริปต์หลัก
if __name__ == "__main__":
    run_sync()
