/*
 * Spider-Sense Band — haptic proximity warning for the blind spots the
 * Ray-Ban Meta camera cannot see (your sides and behind you).
 *
 * Four VL53L1X time-of-flight sensors watch for APPROACHING objects and
 * drive one coin vibration motor each, through a ULN2803A.
 *
 * The core idea (from MateoTechLab's spider-sense glasses): do NOT alert on
 * distance — a wall one metre away is not a threat. Alert on TIME TO
 * COLLISION: distance divided by closing speed. A slow hand 30 cm away is
 * more urgent than a fast car 4 m away, and only TTC gets that right.
 *
 * The haptic loop runs entirely on this board. BLE is telemetry only — never
 * put the phone in the safety path, its latency is 100-300 ms.
 *
 * Board:   ESP32 DevKit V1 (see README for ESP32-C3 pin mapping)
 * Library: "VL53L1X" by Pololu  (Library Manager)
 */

#include <Wire.h>
#include <VL53L1X.h>

// ============================ CONFIG ============================

// Set to 1 to just cycle the motors on boot and stop — use this to verify
// wiring before touching the sensors (build step 1).
#define MOTOR_SELFTEST 0

// Set to 0 while bench-testing to save flash and boot time.
#define ENABLE_BLE 1

#define SENSOR_COUNT 4

struct SensorCfg {
  uint8_t xshutPin;   // VL53L1X XSHUT
  uint8_t motorPin;   // ULN2803A input for this direction's motor
  const char *name;
};

// Pins chosen to avoid ESP32 strapping/flash pins (6-11) and input-only pins (34-39).
const SensorCfg CFG[SENSOR_COUNT] = {
    {25, 32, "left"},
    {26, 33, "right"},
    {27, 18, "rear-L"},
    {14, 19, "rear-R"},
};

const uint8_t I2C_SDA = 21;
const uint8_t I2C_SCL = 22;

// --- detection tuning (the numbers you will actually adjust) ---
const float MAX_RANGE_M      = 3.0f;   // ignore anything further than this
const float MIN_CLOSING_MPS  = 0.4f;   // below this it is not "approaching"
const float TTC_ALERT_S      = 2.0f;   // start buzzing at this time-to-impact
const float TTC_MAX_S        = 0.3f;   // full strength at this time-to-impact
const float VEL_SMOOTHING    = 0.3f;   // EMA alpha: lower = smoother, more lag
const uint32_t STALE_MS      = 400;    // history older than this is untrustworthy

// --- motor tuning ---
const uint8_t MOTOR_MIN_DUTY  = 90;    // below this an ERM motor just hums
const uint8_t MOTOR_MAX_DUTY  = 200;   // caps ~3.1 V from a 4.0 V LiPo (motors are 3 V)
const uint8_t MOTOR_KICK_DUTY = 255;   // brief full power to overcome stiction
const uint16_t MOTOR_KICK_MS  = 20;
const uint16_t PWM_FREQ_HZ    = 1000;
const uint8_t PWM_RESOLUTION  = 8;

// VL53L1X: 33 ms budget gives ~30 Hz per sensor, a good latency/noise balance.
const uint32_t TIMING_BUDGET_US = 33000;
const uint32_t INTERMEASUREMENT_MS = 33;

// ============================ STATE ============================

VL53L1X sensors[SENSOR_COUNT];

struct Track {
  float prevDist = 0.0f;      // metres
  uint32_t prevMs = 0;
  float velFiltered = 0.0f;   // m/s, positive = approaching
  bool hasHistory = false;
  uint8_t duty = 0;
  bool kicking = false;
  uint32_t kickStartMs = 0;
};
Track tracks[SENSOR_COUNT];

// ============================ BLE ============================
#if ENABLE_BLE
#include <BLE2902.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>

// Custom 128-bit UUIDs — the Android app subscribes to the notify characteristic.
#define SVC_UUID "6f9d0001-b5a3-f393-e0a9-e50e24dcca9e"
#define CHR_UUID "6f9d0002-b5a3-f393-e0a9-e50e24dcca9e"

BLECharacteristic *bleChr = nullptr;
bool bleConnected = false;
uint32_t lastNotifyMs = 0;
const uint32_t NOTIFY_INTERVAL_MS = 120;  // cap BLE chatter; haptics are local anyway

class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer *s) override { bleConnected = true; }
  void onDisconnect(BLEServer *s) override {
    bleConnected = false;
    BLEDevice::startAdvertising();  // allow reconnect
  }
};

void setupBle() {
  BLEDevice::init("SpiderSense");
  BLEServer *server = BLEDevice::createServer();
  server->setCallbacks(new ServerCallbacks());
  BLEService *svc = server->createService(SVC_UUID);
  bleChr = svc->createCharacteristic(
      CHR_UUID, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);
  bleChr->addDescriptor(new BLE2902());
  svc->start();
  BLEAdvertising *adv = BLEDevice::getAdvertising();
  adv->addServiceUUID(SVC_UUID);
  adv->setScanResponse(true);
  BLEDevice::startAdvertising();
}

// Notify only the most urgent direction — that is all the phone needs to speak.
void notifyPhone() {
  if (!bleConnected || bleChr == nullptr) return;
  uint32_t now = millis();
  if (now - lastNotifyMs < NOTIFY_INTERVAL_MS) return;

  int worst = -1;
  float worstTtc = 1e9f;
  for (int i = 0; i < SENSOR_COUNT; i++) {
    if (tracks[i].duty == 0 || tracks[i].velFiltered <= 0.0f) continue;
    float ttc = tracks[i].prevDist / tracks[i].velFiltered;
    if (ttc < worstTtc) { worstTtc = ttc; worst = i; }
  }
  if (worst < 0) return;

  lastNotifyMs = now;
  char buf[96];
  snprintf(buf, sizeof(buf), "{\"dir\":\"%s\",\"d\":%.2f,\"v\":%.2f,\"ttc\":%.2f}",
           CFG[worst].name, tracks[worst].prevDist, tracks[worst].velFiltered, worstTtc);
  bleChr->setValue((uint8_t *)buf, strlen(buf));
  bleChr->notify();
}
#endif  // ENABLE_BLE

// ============================ MOTORS ============================

// Indexed by sensor, so the LEDC channel mapping stays correct no matter which
// GPIOs you assign in CFG.
void motorAttach(int i) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcAttach(CFG[i].motorPin, PWM_FREQ_HZ, PWM_RESOLUTION);
#else
  ledcSetup(i, PWM_FREQ_HZ, PWM_RESOLUTION);
  ledcAttachPin(CFG[i].motorPin, i);
#endif
}

void motorWrite(int i, uint8_t duty) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcWrite(CFG[i].motorPin, duty);
#else
  ledcWrite(i, duty);  // channel i, bound in motorAttach()
#endif
}

// ============================ SENSORS ============================

bool setupSensors() {
  // All VL53L1X ship at address 0x29, so they must be brought up one at a time.
  // XSHUT is pulled up on the breakout: drive LOW to hold in reset, release to
  // high-Z (INPUT) to enable. Never drive it HIGH — the part is 2.8 V logic.
  for (int i = 0; i < SENSOR_COUNT; i++) {
    pinMode(CFG[i].xshutPin, OUTPUT);
    digitalWrite(CFG[i].xshutPin, LOW);
  }
  delay(50);

  bool allOk = true;
  for (int i = 0; i < SENSOR_COUNT; i++) {
    pinMode(CFG[i].xshutPin, INPUT);  // release this one only
    delay(50);

    sensors[i].setTimeout(500);
    if (!sensors[i].init()) {
      Serial.printf("[FAIL] sensor %d (%s) did not init — check wiring/XSHUT\n", i,
                    CFG[i].name);
      allOk = false;
      continue;
    }
    sensors[i].setAddress(0x30 + i);  // move off 0x29 before releasing the next
    sensors[i].setDistanceMode(VL53L1X::Long);
    sensors[i].setMeasurementTimingBudget(TIMING_BUDGET_US);
    sensors[i].startContinuous(INTERMEASUREMENT_MS);
    Serial.printf("[ok] sensor %d (%s) at 0x%02X\n", i, CFG[i].name, 0x30 + i);
  }
  return allOk;
}

// ============================ CORE ============================

// Map time-to-collision to motor strength: sooner impact = stronger buzz.
uint8_t dutyForTtc(float ttc) {
  if (ttc >= TTC_ALERT_S) return 0;
  if (ttc <= TTC_MAX_S) return MOTOR_MAX_DUTY;
  float t = (TTC_ALERT_S - ttc) / (TTC_ALERT_S - TTC_MAX_S);  // 0..1
  return (uint8_t)(MOTOR_MIN_DUTY + t * (MOTOR_MAX_DUTY - MOTOR_MIN_DUTY));
}

void updateSensor(int i) {
  if (!sensors[i].dataReady()) return;

  uint16_t mm = sensors[i].read(false);
  uint32_t now = millis();
  Track &tk = tracks[i];

  bool valid = !sensors[i].timeoutOccurred() &&
               sensors[i].ranging_data.range_status == VL53L1X::RangeValid;
  float dist = mm / 1000.0f;

  if (!valid || dist <= 0.0f || dist > MAX_RANGE_M) {
    tk.hasHistory = false;   // do not compute velocity across a gap
    tk.velFiltered = 0.0f;
    tk.duty = 0;
    return;
  }

  if (!tk.hasHistory || (now - tk.prevMs) > STALE_MS) {
    tk.prevDist = dist;
    tk.prevMs = now;
    tk.hasHistory = true;
    tk.velFiltered = 0.0f;
    tk.duty = 0;  // otherwise a stale duty keeps the motor buzzing
    return;
  }

  float dt = (now - tk.prevMs) / 1000.0f;
  if (dt <= 0.0f) return;

  float vel = (tk.prevDist - dist) / dt;  // positive = getting closer
  tk.velFiltered = VEL_SMOOTHING * vel + (1.0f - VEL_SMOOTHING) * tk.velFiltered;
  tk.prevDist = dist;
  tk.prevMs = now;

  if (tk.velFiltered < MIN_CLOSING_MPS) {
    tk.duty = 0;
    return;
  }
  tk.duty = dutyForTtc(dist / tk.velFiltered);
}

// ERM motors will not start from rest at low duty, so kick briefly at full power.
void driveMotor(int i) {
  Track &tk = tracks[i];

  if (tk.duty == 0) {
    tk.kicking = false;
    motorWrite(i, 0);
    return;
  }
  if (!tk.kicking) {
    tk.kicking = true;
    tk.kickStartMs = millis();
    motorWrite(i, MOTOR_KICK_DUTY);
    return;
  }
  if (millis() - tk.kickStartMs < MOTOR_KICK_MS) return;  // still kicking
  motorWrite(i, tk.duty);
}

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\nSpider-Sense Band starting");

  for (int i = 0; i < SENSOR_COUNT; i++) {
    motorAttach(i);
    motorWrite(i, 0);
  }

#if MOTOR_SELFTEST
  Serial.println("MOTOR_SELFTEST: pulsing each motor in turn");
  while (true) {
    for (int i = 0; i < SENSOR_COUNT; i++) {
      Serial.printf("  motor %d (%s)\n", i, CFG[i].name);
      motorWrite(i, MOTOR_MAX_DUTY);
      delay(600);
      motorWrite(i, 0);
      delay(400);
    }
  }
#endif

  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(400000);
  if (!setupSensors()) {
    Serial.println("WARNING: continuing with partial sensors");
  }

#if ENABLE_BLE
  setupBle();
  Serial.println("BLE advertising as \"SpiderSense\"");
#endif

  Serial.println("Running. Columns: name distance_m velocity_mps ttc_s duty");
}

void loop() {
  for (int i = 0; i < SENSOR_COUNT; i++) {
    updateSensor(i);
    driveMotor(i);
  }

#if ENABLE_BLE
  notifyPhone();
#endif

  // Telemetry for tuning: only prints when something is actually alerting,
  // so a quiet room stays quiet on the serial monitor too.
  static uint32_t lastPrint = 0;
  if (millis() - lastPrint > 150) {
    lastPrint = millis();
    for (int i = 0; i < SENSOR_COUNT; i++) {
      if (tracks[i].duty == 0) continue;
      float ttc = tracks[i].velFiltered > 0 ? tracks[i].prevDist / tracks[i].velFiltered : -1.0f;
      Serial.printf("%-7s %.2f %.2f %.2f %u\n", CFG[i].name, tracks[i].prevDist,
                    tracks[i].velFiltered, ttc, tracks[i].duty);
    }
  }
}
