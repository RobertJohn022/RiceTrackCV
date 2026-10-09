// ESP32 + MPU-6050 (tilt) + NEO-6M (GPS) -> USB serial for the RiceTrack app
//
// Wiring
//   MPU-6050 (GY-521):  VCC -> 3V3,  GND -> GND,  SDA -> GPIO 21,  SCL -> GPIO 22
//   NEO-6M:             VCC -> 3V3,  GND -> GND,  TX  -> GPIO 16 (ESP32 RX2),  RX -> GPIO 17 (ESP32 TX2)
//   (GPIO 16/17 are free on a normal ESP32 DevKit. ESP32-WROVER uses them for PSRAM:
//    pick other pins in GPS_RX_PIN / GPS_TX_PIN if that is your board.)
//
// Library needed (Arduino IDE > Library Manager):  "TinyGPSPlus" by Mikal Hart
//
// Output (115200 baud):
//   $IMU,<roll>,<pitch>          20 Hz, degrees
//   $NOIMU                       MPU-6050 did not answer on the I2C bus
//   $GPS,1,<lat>,<lon>,<sats>    1 Hz, valid position fix
//   $GPS,0,,,<sats>              1 Hz, GPS module talking but no fix yet
//   $NOGPS                       1 Hz, nothing coming from the GPS module

#include <Wire.h>
#include <TinyGPSPlus.h>

// ---------- MPU-6050 ----------
const int SDA_PIN = 21;
const int SCL_PIN = 22;
const uint8_t MPU_ADDR = 0x68;        // 0x69 if the AD0 pin is pulled high
const unsigned long IMU_SEND_MS = 50; // 20 Hz
const float SMOOTHING = 0.2f;         // 0..1, lower = smoother but slower

float roll = 0, pitch = 0;
bool imuReady = false;
bool firstSample = true;
unsigned long lastImuSend = 0;

// ---------- NEO-6M ----------
const int GPS_RX_PIN = 16;            // ESP32 RX2  <- GPS TX
const int GPS_TX_PIN = 17;            // ESP32 TX2  -> GPS RX
const unsigned long GPS_SEND_MS = 1000;
const unsigned long GPS_SILENCE_MS = 3000;   // no valid NMEA sentence for this long = module gone

TinyGPSPlus gps;
HardwareSerial GPSSerial(2);
uint32_t lastGoodSentences = 0;
unsigned long lastGpsData = 0;        // when the last checksum-valid sentence arrived; 0 = never
unsigned long lastGpsSend = 0;

bool mpuInit() {
  Wire.beginTransmission(MPU_ADDR);
  if (Wire.endTransmission() != 0) return false;   // nothing answered at this address
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B);                                // PWR_MGMT_1
  Wire.write(0x00);                                // wake from sleep
  return Wire.endTransmission() == 0;
}

int16_t read16() {
  uint8_t hi = Wire.read();                        // separate statements: C++ does not
  uint8_t lo = Wire.read();                        // guarantee left-to-right evaluation
  return (int16_t)((hi << 8) | lo);
}

bool readAccel(float &ax, float &ay, float &az) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);                                // ACCEL_XOUT_H
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((int)MPU_ADDR, 6) != 6) return false;
  ax = read16() / 16384.0f;                        // +-2 g range -> 16384 LSB/g
  ay = read16() / 16384.0f;
  az = read16() / 16384.0f;
  return true;
}

void sendImu() {
  if (!imuReady) {
    imuReady = mpuInit();
    firstSample = true;
  }

  float ax, ay, az;
  if (imuReady && readAccel(ax, ay, az)) {
    float r = atan2f(ay, az) * 180.0f / PI;
    float p = atan2f(-ax, sqrtf(ay * ay + az * az)) * 180.0f / PI;
    if (firstSample) {
      roll = r; pitch = p; firstSample = false;
    } else {
      roll  += SMOOTHING * (r - roll);
      pitch += SMOOTHING * (p - pitch);
    }
    Serial.printf("$IMU,%.1f,%.1f\n", roll, pitch);
  } else {
    imuReady = false;                              // retry init next cycle (hot-plug friendly)
    Serial.println("$NOIMU");
  }
}

void sendGps(unsigned long now) {
  unsigned sats = gps.satellites.isValid() ? gps.satellites.value() : 0;
  if (lastGpsData == 0 || now - lastGpsData > GPS_SILENCE_MS) {
    Serial.println("$NOGPS");
  } else if (gps.location.isValid() && gps.location.age() < GPS_SILENCE_MS) {
    Serial.printf("$GPS,1,%.6f,%.6f,%u\n", gps.location.lat(), gps.location.lng(), sats);
  } else {
    Serial.printf("$GPS,0,,,%u\n", sats);
  }
}

void setup() {
  Serial.begin(115200);
  Wire.begin(SDA_PIN, SCL_PIN);
  GPSSerial.begin(9600, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);   // NEO-6M default is 9600 baud
}

void loop() {
  unsigned long now = millis();

  // Always drain the GPS UART first so its buffer never overflows.
  while (GPSSerial.available()) gps.encode(GPSSerial.read());
  // Count only sentences with a valid checksum: a floating/unpowered GPS line produces
  // random noise characters, which must not count as "GPS present".
  if (gps.passedChecksum() != lastGoodSentences) {
    lastGoodSentences = gps.passedChecksum();
    lastGpsData = now;
  }

  if (now - lastImuSend >= IMU_SEND_MS) {
    lastImuSend = now;
    sendImu();
  }
  if (now - lastGpsSend >= GPS_SEND_MS) {
    lastGpsSend = now;
    sendGps(now);
  }
}
