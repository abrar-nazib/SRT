/*
 * Military Tracking System - Arduino Code
 * Controls 2 servo motors (pan/tilt) and a laser
 */
#include <Arduino.h>
#include <Servo.h>

Servo panServo;
Servo tiltServo;

const int PAN_PIN = 6;
const int TILT_PIN = 5;
const int LASER_PIN = 13;

// Current positions
float currentPan = 90;
float currentTilt = 90;

// Servo limits
const int PAN_MIN = 0;
const int PAN_MAX = 180;
const int TILT_MIN = 0;
const int TILT_MAX = 180;

// Smoothing
const float SMOOTH_FACTOR = 0.3;

void testServoPins();
void parseCommand(String command);

void setup()
{
  Serial.begin(115200);

  panServo.attach(PAN_PIN);
  tiltServo.attach(TILT_PIN);
  pinMode(LASER_PIN, OUTPUT);

  // Center servos
  panServo.write(currentPan);
  tiltServo.write(currentTilt);

  digitalWrite(LASER_PIN, LOW);

  Serial.println("Arduino Tracking System Ready");
}

void loop()
{
  if (Serial.available() > 0)
  {
    String command = Serial.readStringUntil('\n');
    parseCommand(command);
  }
}

void testServoPins()
{
  // Test servo pins by moving them to their limits
  Serial.println("Testing servo pins...");

  Serial.print("Pan Servo: ");
  for (int angle = PAN_MIN; angle <= PAN_MAX; angle += 10)
  {
    panServo.write(angle);
    delay(250);
  }

  Serial.print("Tilt Servo: ");
  for (int angle = TILT_MIN; angle <= TILT_MAX; angle += 10)
  {
    tiltServo.write(angle);
    delay(250);
  }

  Serial.println("Reversing servo directions...");
  Serial.print("Pan Servo: ");
  for (int angle = PAN_MAX; angle >= PAN_MIN; angle -= 10)
  {
    panServo.write(angle);
    delay(250);
  }

  Serial.print("Tilt Servo: ");
  for (int angle = TILT_MAX; angle >= TILT_MIN; angle -= 10)
  {
    tiltServo.write(angle);
    delay(250);
  }

  Serial.println("Servo pin test complete.");
}

void parseCommand(String command)
{
  // Expected format: "+2.5:-3.5:0"
  int firstColon = command.indexOf(':');
  int secondColon = command.indexOf(':', firstColon + 1);

  if (firstColon > 0 && secondColon > firstColon)
  {
    float panDelta = command.substring(0, firstColon).toFloat();
    float tiltDelta = command.substring(firstColon + 1, secondColon).toFloat();
    int laser = command.substring(secondColon + 1).toInt();

    // Update positions with smoothing
    float targetPan = currentPan - panDelta;
    float targetTilt = currentTilt + tiltDelta;

    // Apply limits
    targetPan = constrain(targetPan, PAN_MIN, PAN_MAX);
    targetTilt = constrain(targetTilt, TILT_MIN, TILT_MAX);

    // Smooth movement
    currentPan = currentPan + (targetPan - currentPan) * SMOOTH_FACTOR;
    currentTilt = currentTilt + (targetTilt - currentTilt) * SMOOTH_FACTOR;
    // currentPan = targetPan; // For simplicity, we can directly set the target
    // currentTilt = targetTilt;

    // Write to servos
    // panServo.write((int)currentPan);
    // tiltServo.write((int)currentTilt);
    panServo.writeMicroseconds((int)map(currentPan, PAN_MIN, PAN_MAX, 700, 2500));
    tiltServo.writeMicroseconds((int)(map(currentTilt, TILT_MIN, TILT_MAX, 700, 2500)));
    // Control laser
    digitalWrite(LASER_PIN, laser ? HIGH : LOW);

    // Send acknowledgment
    // Serial.print("PAN:");
    // Serial.print(currentPan);
    // Serial.print(",TILT:");
    // Serial.print(currentTilt);
    // Serial.print(",LASER:");
    // Serial.println(laser);
  }
}