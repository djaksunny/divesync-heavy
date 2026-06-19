// Linear Actuator Test Code - Simplified (full speed bang-bang control)
// Stripped down from PID version: takes 1 / 0 / -1 over Serial
//   1  -> full speed forward (inward)
//   0  -> stop
//  -1  -> full speed backward (outward)

#include <Arduino.h>

// Define actuator signals and feedback pin
#define ACT_SIG1 4
#define ACT_SIG2 5
#define ACT_FB 0

#define _pos_th 4050  // Upper feedback bound (fully forward)
#define _neg_th 50    // Lower feedback bound (fully back)

volatile int _cmd = 0; // Current command: 1, 0, or -1

void actuate(int _dir);

void setup() {
  pinMode(ACT_SIG1, OUTPUT);
  pinMode(ACT_SIG2, OUTPUT);
  pinMode(ACT_FB, INPUT);

  Serial.begin(115200);
  Serial.println("Linear Actuator Bang-Bang Control started!!!");
  Serial.println("Send 1 (forward), 0 (stop), or -1 (back)");

  actuate(0); // Start stopped
}

void loop() {
  // Check for new command over Serial
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    int _val = input.toInt();

    if (_val > 0) {
      _cmd = 1;
    } else if (_val < 0) {
      _cmd = -1;
    } else {
      _cmd = 0;
    }

    Serial.print("New Command: ");
    Serial.println(_cmd);
  }

  actuate(_cmd);

  Serial.print("RAW Actuator Feedback: ");
  Serial.println(analogRead(ACT_FB));

  delay(50);
}

// Drive the linear actuator at full speed in the given direction,
// respecting the configured travel limits.
void actuate(int _dir) {
  int _pos_now = analogRead(ACT_FB);

  // Guard against driving past the configured bounds
  if (_pos_now >= _pos_th && _dir > 0) {
    _dir = 0;
  }
  if (_pos_now <= _neg_th && _dir < 0) {
    _dir = 0;
  }

  if (_dir > 0) {        // Full speed forward (inward)
    analogWrite(ACT_SIG1, 0);
    analogWrite(ACT_SIG2, 200);
  } else if (_dir < 0) {  // Full speed backward (outward)
    analogWrite(ACT_SIG2, 0);
    analogWrite(ACT_SIG1, 200);
  } else {                // Stop
    analogWrite(ACT_SIG1, 200);
    analogWrite(ACT_SIG2, 200);
  }
}
