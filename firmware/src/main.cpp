#include <Arduino.h>
#include <Wire.h>
#include <MS5837.h>

// =========================
// Pin definitions
// =========================
#define SYG_IN1     4
#define SYG_IN2     5
#define SYG_FB      0       // Potentiometer feedback (analog in)
#define BAR_SDA     19
#define BAR_SCL     18
#define BATT_SENSE  3

// =========================
// Actuator limits
// =========================
#define SYG_MAX 4050        // Safe upper travel limit
#define SYG_MIN 250         // Safe lower travel limit

// =========================
// PWM settings (LEDC)
// =========================
#define PWM_FREQ    25000   // 25 kHz: above human hearing to eliminate whine
#define PWM_RES     8       // 8-bit resolution (0-255)
#define PWM_CH1     0       // LEDC hardware channel for IN1
#define PWM_CH2     1       // LEDC hardware channel for IN2

// =========================
// General settings
// =========================
#define NUM_SAMPLES_ACTUATOR        10
#define SERIAL_BAUD                 115200
#define TELEMETRY_PERIOD_MS         50
#define ATM_PRESSURE_MBAR           1024
#define DEPTH_SENSOR_REQUIRED       true

// =========================
// Battery ADC calibration
// =========================
#define ADC_MAX_COUNTS              4095.0f
#define ADC_REF_VOLTAGE             3.3f
#define BATT_DIVIDER_R_TOP_OHM      4700.0f
#define BATT_DIVIDER_R_BOTTOM_OHM   1500.0f

// =========================
// Fluid density
// =========================
const int FLUID_DENSITY = 1000;  // kg/m^3

// =========================
// Global state
// =========================
MS5837 BAR;

volatile int  g_motor_cmd      = 0;
unsigned long g_last_telemetry = 0;
bool          g_depth_ok       = false;

// =========================
// Function declarations
// =========================
int   getActuator(int n = NUM_SAMPLES_ACTUATOR);
void  actuate(int u);
void  processSerial();
void  sendTelemetry();
bool  updateDepthSensor(float &pressure_mbar, float &temperature_c, float &depth_m);
int   clampMotorCommand(int u);
float readBatteryVoltage();

// =========================
// Setup
// =========================
void setup() {
    pinMode(SYG_FB,     INPUT);
    pinMode(BATT_SENSE, INPUT);
    analogReadResolution(12);
    analogSetPinAttenuation(BATT_SENSE, ADC_0db);

    Serial.begin(SERIAL_BAUD);
    delay(200);

    // LEDC PWM init
    ledcSetup(PWM_CH1, PWM_FREQ, PWM_RES);
    ledcSetup(PWM_CH2, PWM_FREQ, PWM_RES);
    ledcAttachPin(SYG_IN1, PWM_CH1);
    ledcAttachPin(SYG_IN2, PWM_CH2);
    actuate(0);  // Brake on startup

    // Depth sensor init — blocks until ready if DEPTH_SENSOR_REQUIRED
    Wire.begin(BAR_SDA, BAR_SCL);

    do {
        if (BAR.init()) {
            BAR.setModel(MS5837::MS5837_02BA);
            BAR.setFluidDensity(FLUID_DENSITY);
            g_depth_ok = true;
            Serial.println("DEPTH_SENSOR_OK");
            break;
        }

        g_depth_ok = false;
        Serial.println("DEPTH_SENSOR_FAIL");

        if (DEPTH_SENSOR_REQUIRED) {
            Serial.println("WAITING_FOR_DEPTH_SENSOR");
            delay(500);
        }
    } while (DEPTH_SENSOR_REQUIRED);

    Serial.println("LOW_LEVEL_DEPTH_ACTUATOR_INTERFACE_READY");
}

// =========================
// Main loop
// =========================
void loop() {
    processSerial();
    actuate(g_motor_cmd);

    if (millis() - g_last_telemetry >= TELEMETRY_PERIOD_MS) {
        g_last_telemetry = millis();
        sendTelemetry();
    }
}

// =========================
// Serial command handling
// =========================
void processSerial() {
    if (!Serial.available()) return;

    String msg = Serial.readStringUntil('\n');
    msg.trim();
    if (msg.length() == 0) return;

    if (msg == "R") {
        sendTelemetry();
        return;
    }

    if (msg == "S") {
        g_motor_cmd = 0;
        actuate(0);
        Serial.println("ACK:STOP");
        return;
    }

    if (msg.startsWith("U:")) {
        int cmd = msg.substring(2).toInt();
        g_motor_cmd = clampMotorCommand(cmd);
        Serial.print("ACK:U:");
        Serial.println(g_motor_cmd);
        return;
    }

    if (msg == "RST") {
        ESP.restart();
    }

    Serial.print("ERR:UNKNOWN_CMD:");
    Serial.println(msg);
}

// =========================
// Telemetry output
// =========================
void sendTelemetry() {
    int   act_raw   = getActuator();
    float battery_v = readBatteryVoltage();

    float pressure_mbar = NAN;
    float temperature_c = NAN;
    float depth_m       = NAN;

    bool ok = updateDepthSensor(pressure_mbar, temperature_c, depth_m);

    // CSV: time_ms, actuator_raw, motor_cmd, depth_m, pressure_mbar, temp_c, depth_ok, battery_v
    Serial.print(millis());         Serial.print(",");
    Serial.print(act_raw);          Serial.print(",");
    Serial.print(g_motor_cmd);      Serial.print(",");
    Serial.print(depth_m, 4);       Serial.print(",");
    Serial.print(pressure_mbar, 2); Serial.print(",");
    Serial.print(temperature_c, 2); Serial.print(",");
    Serial.print(ok ? 1 : 0);       Serial.print(",");
    Serial.println(battery_v, 2);
}

// =========================
// Battery voltage read
// =========================
float readBatteryVoltage() {
    float v_sense     = analogReadMilliVolts(BATT_SENSE);
    float divider_gain = (BATT_DIVIDER_R_TOP_OHM + BATT_DIVIDER_R_BOTTOM_OHM)
                         / BATT_DIVIDER_R_BOTTOM_OHM;
    return v_sense * divider_gain / 1000.0f;
}

// =========================
// Depth sensor update
// =========================
bool updateDepthSensor(float &pressure_mbar, float &temperature_c, float &depth_m) {
    if (!g_depth_ok) return false;

    BAR.read();
    pressure_mbar = BAR.pressure();
    temperature_c = BAR.temperature();
    depth_m       = BAR.depth();

    return !(isnan(pressure_mbar) || isnan(temperature_c) || isnan(depth_m));
}

// =========================
// Actuator drive (DRV8251 via LEDC)
// =========================
void actuate(int u) {
    int pos = analogRead(SYG_FB);

    // Hard software travel limits
    if (pos >= SYG_MAX && u > 0) u = 0;
    if (pos <= SYG_MIN && u < 0) u = 0;

    u = constrain(u, -255, 255);

    if (u > 0) {                    // Extend
        ledcWrite(PWM_CH1, 0);
        ledcWrite(PWM_CH2, u);
    } else if (u < 0) {             // Retract
        ledcWrite(PWM_CH2, 0);
        ledcWrite(PWM_CH1, -u);
    } else {                        // Brake: both inputs HIGH
        ledcWrite(PWM_CH1, 255);
        ledcWrite(PWM_CH2, 255);
    }
}

// =========================
// Read actuator position (averaged)
// =========================
int getActuator(int n) {
    int sum = 0;
    for (int i = 0; i < n; i++) {
        sum += analogRead(SYG_FB);
    }
    return sum / n;
}

// =========================
// Clamp command to valid range
// =========================
int clampMotorCommand(int u) {
    return constrain(u, -255, 255);
}
