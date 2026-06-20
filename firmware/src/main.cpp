#include <Arduino.h>

#define ACT_SIG1 4
#define ACT_SIG2 5
#define ACT_FB   A0  // Explicitly use A0 for proper analog reading

#define _pos_th 4050
#define _neg_th 50

// --- LEDC Configuration ---
#define PWM_FREQ 25000 // 25 kHz: Above human hearing to eliminate whine
#define PWM_RES  8     // 8-bit resolution (0-255) to match Python logic
#define PWM_CH1  0     // ESP32 Hardware Timer Channel 0
#define PWM_CH2  1     // ESP32 Hardware Timer Channel 1

volatile int pwm = 0;

void actuate(int dir);

void setup() {
    pinMode(ACT_FB, INPUT);
    Serial.begin(115200);

    // 1. Configure the LEDC timers for the high-frequency PWM
    ledcSetup(PWM_CH1, PWM_FREQ, PWM_RES);
    ledcSetup(PWM_CH2, PWM_FREQ, PWM_RES);

    // 2. Attach the timers directly to your DRV8251 motor pins
    ledcAttachPin(ACT_SIG1, PWM_CH1);
    ledcAttachPin(ACT_SIG2, PWM_CH2);

    // Initialize to stopped
    actuate(0);
}

void loop() {
    // Only execute and send data if Python speaks first
    if (Serial.available() > 0) {
        String input = Serial.readStringUntil('\n');
        pwm = constrain(input.toInt(), -255, 255);

        actuate(pwm);

        // Handshake response: Send the 'I:' prefix along with the feedback
        Serial.print("I:");
        Serial.println(analogRead(ACT_FB));
    }
}

void actuate(int dir) {
    int _pos_now = analogRead(ACT_FB);

    // Boundary safety limits
    if (_pos_now >= _pos_th && dir > 0) {
        dir = 0;
    }
    if (_pos_now <= _neg_th && dir < 0) {
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
