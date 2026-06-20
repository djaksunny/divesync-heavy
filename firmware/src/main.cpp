#include <Arduino.h>

#define ACT_SIG1 4
#define ACT_SIG2 5
#define ACT_FB 0

#define _pos_th 4050
#define _neg_th 50

volatile int pwm = 0;

void actuate(int dir);

void setup() {
  pinMode(ACT_SIG1, OUTPUT);
  pinMode(ACT_SIG2, OUTPUT);
  pinMode(ACT_FB, INPUT);

  Serial.begin(115200);
  Serial.println("Actuator PWM test started.");

  actuate(0);
}

void loop() {
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    pwm = constrain(input.toInt(), -255, 255);

    Serial.print("New Command: ");
    Serial.println(pwm);
  }

  if (pwm >= -255 && pwm <= 255) {
    actuate(pwm);
  }

  Serial.print("RAW Actuator Feedback: ");
  Serial.println(analogRead(ACT_FB));

  delay(50);
}

void actuate(int dir) {
  int _pos_now = analogRead(ACT_FB);

  if (_pos_now >= _pos_th && dir > 0) {
    dir = 0;
  }
  if (_pos_now <= _neg_th && dir < 0) {
    dir = 0;
  }

  if (dir > 0) {
    analogWrite(ACT_SIG1, 0);
    analogWrite(ACT_SIG2, dir);
  } else if (dir < 0) {
    analogWrite(ACT_SIG2, 0);
    analogWrite(ACT_SIG1, -dir);
  } else {
    analogWrite(ACT_SIG1, 255);
    analogWrite(ACT_SIG2, 255);
  }
}
