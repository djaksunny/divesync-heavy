#include <Arduino.h>
#include <Wire.h>
#include <MS5837.h>

// --- SYRINGE SETUP ---
#define SYG_IN1 4
#define SYG_IN2 5
#define SYG_FB  0      // Analog pin for potentiometer feedback
#define SYG_MAX 4050   // Safe upper limit for actuator
#define SYG_MIN 50     // Safe lower limit for actuator

void actuate(int dir);

// --- I2C SETUP ---
#define BAR_SDA 19
#define BAR_SCL 18

// --- PWM SETUP ---
#define PWM_FREQ 25000 // 25 kHz: Above human hearing to eliminate whine
#define PWM_RES  8     // 8-bit resolution (0-255) to match Python logic
#define PWM_CH1  0     // ESP32 Hardware Timer Channel 0
#define PWM_CH2  1     // ESP32 Hardware Timer Channel 1
volatile int pwm = 0;

// --- BAR SETUP ---
const int FLUID_DENSITY = 997; // kg/m^3, 997 for freshwater
MS5837 BAR;

void setup() {
    // --- SYRINGE SETUP ---
    pinMode(SYG_FB, INPUT);
    Serial.begin(115200);

    ledcSetup(PWM_CH1, PWM_FREQ, PWM_RES);
    ledcSetup(PWM_CH2, PWM_FREQ, PWM_RES);

    ledcAttachPin(SYG_IN1, PWM_CH1);
    ledcAttachPin(SYG_IN2, PWM_CH2);

    actuate(0);

    // --- BAR INIT ---
    Wire.begin(BAR_SDA, BAR_SCL);
    bool BAR_OK = false;

    do {
    if (BAR.init()) {
      BAR.setModel(MS5837::MS5837_02BA);
      BAR.setFluidDensity(FLUID_DENSITY);
      Serial.println("DEPTH_SENSOR_OK");
      BAR_OK = true;
    } else {
      Serial.println("DEPTH_SENSOR_FAIL");
      delay(1000);
    }
  } while (BAR_OK == false);
}

void loop() {
    if (Serial.available() > 0) {
        String input = Serial.readStringUntil('\n');

        int cmd = input.toInt();
        pwm = constrain(cmd, -255, 255);

        actuate(pwm);

        BAR.read();

        Serial.print(analogRead(SYG_FB));
        Serial.print(",");
        Serial.println(BAR.depth());
    }
}

void actuate(int dir) {
    int pos = analogRead(SYG_FB);

    // Boundary safety limits
    if (pos >= SYG_MAX && dir > 0) {
        dir = 0;
    }
    if (pos <= SYG_MIN && dir < 0) {
        dir = 0;
    }

    // DRV8251 Control Logic using LEDC
    if (dir > 0) {
        ledcWrite(PWM_CH1, 0);
        ledcWrite(PWM_CH2, dir);
    } else if (dir < 0) {
        ledcWrite(PWM_CH2, 0);
        ledcWrite(PWM_CH1, -dir);
    } else {
        // BRAKE MODE: Both inputs HIGH (255 maxes out the 8-bit resolution)
        ledcWrite(PWM_CH1, 255);
        ledcWrite(PWM_CH2, 255);
    }
}
