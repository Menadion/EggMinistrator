/*
  EggMinistrator -- ESP32-S3 firmware (load cell + OLED + LEDs + buzzer only)
  ----------------------------------------------------------------------------
  This board does NOT handle the camera. The camera is a regular USB webcam
  plugged straight into the same computer that runs egg_inspector_yolo.py --
  that app already captures and classifies images on its own. This board's
  only job is the physical side: read the load cell, send the weight to the
  computer over USB serial, and show whatever result comes back on the OLED
  / LEDs / buzzer.

  NOT COMPILE-TESTED -- I don't have this hardware or an Arduino toolchain
  to verify it on. Grounded in current documentation for the pin
  restrictions and library APIs, but treat it as a first draft to debug on
  real hardware, the way you would any code from any source you haven't
  run yet.

  ============================================================================
  REQUIRED LIBRARIES (Arduino IDE > Sketch > Include Library > Manage
  Libraries):
    - "HX711 Arduino Library" by Bogdan Necula
    - "Adafruit SSD1306" by Adafruit
    - "Adafruit GFX Library" by Adafruit
    - "ArduinoJson" by Benoit Blanchon (v6.x)
  Board: Tools > Board > ESP32 Arduino > pick your specific ESP32-S3 board
  (e.g. "ESP32S3 Dev Module"). Needs the "esp32" board package installed.

  ============================================================================
  SERIAL PROTOCOL (plain text, one line at a time, 115200 baud):
    ESP32 -> PC:  W:<grams>\n                      e.g.  W:58.23
    PC -> ESP32:  R:<label>:<confidence>\n          e.g.  R:good:0.83
                  label is one of: good, defective, not_egg

  Calibrate LOADCELL_CALIBRATION_FACTOR the same way regardless of which
  ESP32 board you use -- see the comment on that constant below.
*/

#include <HX711.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <ArduinoJson.h>

// -----------------------------------------------------------------------
// Pins. ESP32-S3 dev boards have far more usable GPIOs than the ESP32-CAM
// did (no camera consuming 15 of them), so this is a much simpler pin
// budget. Explicitly avoided: GPIO0/3/45/46 (strapping pins -- can put
// the board into download mode or the wrong boot voltage if pulled the
// wrong way at power-on), GPIO19/20 (used by native USB-JTAG on most
// ESP32-S3 boards), and GPIO26-37 (SPI flash / PSRAM on boards that have
// it -- varies by exact module, safest to just avoid the whole range).
#define HX711_DT_PIN   4
#define HX711_SCK_PIN  5
#define OLED_SDA_PIN   8
#define OLED_SCL_PIN   9
#define BUZZER_PIN    10
#define LED_RED_PIN   11
#define LED_GREEN_PIN 12
#define LED_BLUE_PIN  13   // only used for the "not an egg" indicator -- see indicateResult()

// HX711 calibration factor -- MUST be calibrated for your specific load
// cell, the same procedure regardless of which ESP32 board drives it:
//   1. Flash a minimal sketch that prints scale.get_units(10) in a loop
//      with nothing on the platform, right after scale.tare().
//   2. Place a known weight (anything you can weigh precisely elsewhere)
//      and note the raw reading.
//   3. LOADCELL_CALIBRATION_FACTOR = raw_reading / known_weight_grams
//   4. Re-flash with that value; confirm get_units() reports correctly
//      for a couple of different test weights before trusting it.
float LOADCELL_CALIBRATION_FACTOR = 2280.0;   // TODO: replace after calibrating

const float EGG_PRESENT_THRESHOLD_G = 20.0;
const float EGG_REMOVED_THRESHOLD_G = 15.0;
const unsigned long WEIGHT_SEND_INTERVAL_MS = 300;

HX711 scale;
Adafruit_SSD1306 display(128, 64, &Wire, -1);

// Declared up here, before handleLine() and showResult() use it. It was
// originally defined further down the file, after its first use, which does
// not compile in C++ -- and the Arduino IDE's auto-generated prototypes make
// it worse, since they reference the type before it exists.
struct InspectionResultLocal {
  String label;
  float confidence;
};

unsigned long lastWeightSend = 0;
bool waitingForResult = false;
unsigned long resultRequestedAt = 0;
const unsigned long RESULT_TIMEOUT_MS = 5000;   // give up waiting and go back to idle

// ---------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_RED_PIN, OUTPUT);
  pinMode(LED_GREEN_PIN, OUTPUT);
  pinMode(LED_BLUE_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(LED_RED_PIN, LOW);
  digitalWrite(LED_GREEN_PIN, LOW);
  digitalWrite(LED_BLUE_PIN, LOW);

  Wire.begin(OLED_SDA_PIN, OLED_SCL_PIN);
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    // CHECK: 0x3C is the usual SSD1306 address; some 0.96" boards use 0x3D.
    Serial.println("OLED not found at 0x3C -- check wiring / try address 0x3D");
  }
  display.setTextColor(SSD1306_WHITE);
  showMessage("Starting...");

  scale.begin(HX711_DT_PIN, HX711_SCK_PIN);
  scale.set_scale(LOADCELL_CALIBRATION_FACTOR);
  scale.tare();   // make sure the platform is empty when this runs

  showMessage("Ready.\nPlace an egg.");
}

// ---------------------------------------------------------------------------
float readWeightGrams() {
  if (!scale.is_ready()) return 0.0;
  return scale.get_units(5);
}

// ---------------------------------------------------------------------------
void loop() {
  readSerialCommands();

  float weight = readWeightGrams();
  unsigned long now = millis();

  if (waitingForResult) {
    if (now - resultRequestedAt > RESULT_TIMEOUT_MS) {
      // The PC never answered (app not running? egg not detected in frame?)
      // -- don't leave the operator staring at "Capturing..." forever.
      showMessage("No response.\nTry again.");
      beepError();
      waitingForResult = false;
    }
    return;   // don't send more weight readings mid-inspection
  }

  if (weight < EGG_PRESENT_THRESHOLD_G) {
    delay(150);
    return;   // nothing on the platform yet
  }

  // An egg just showed up: send its weight and wait for the PC's verdict.
  if (now - lastWeightSend > WEIGHT_SEND_INTERVAL_MS) {
    showMessage("Egg detected.\nSending weight...");
    Serial.print("W:");
    Serial.println(weight, 2);
    lastWeightSend = now;
    waitingForResult = true;
    resultRequestedAt = now;
  }
}

// ---------------------------------------------------------------------------
// Reads lines like "R:good:0.83" from the PC and acts on them.
void readSerialCommands() {
  static String line = "";
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      handleLine(line);
      line = "";
    } else if (c != '\r') {
      line += c;
    }
  }
}

void handleLine(const String &line) {
  if (!line.startsWith("R:")) return;

  int firstColon = line.indexOf(':', 2);
  if (firstColon < 0) return;

  String label = line.substring(2, firstColon);
  float confidence = line.substring(firstColon + 1).toFloat();

  InspectionResultLocal result{label, confidence};
  showResult(result);
  indicateResult(result);
  waitingForResult = false;

  // Wait for the egg to be removed before watching for the next one
  while (readWeightGrams() > EGG_REMOVED_THRESHOLD_G) {
    delay(200);
  }
  digitalWrite(LED_RED_PIN, LOW);
  digitalWrite(LED_GREEN_PIN, LOW);
  digitalWrite(LED_BLUE_PIN, LOW);
  showMessage("Ready.\nPlace an egg.");
}

// ---------------------------------------------------------------------------
void showMessage(const String &msg) {
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println(msg);
  display.display();
}

void showResult(const InspectionResultLocal &result) {
  display.clearDisplay();
  display.setTextSize(2);
  display.setCursor(0, 0);
  display.println(result.label);
  display.setTextSize(1);
  display.setCursor(0, 24);
  display.print("Conf: ");
  display.print(result.confidence * 100.0, 0);
  display.println("%");
  display.display();
}

// ---------------------------------------------------------------------------
// FR-15: "Indicate the classification result at the inspection station
// through a visual indicator and an audible signal."
void indicateResult(const InspectionResultLocal &result) {
  digitalWrite(LED_RED_PIN, LOW);
  digitalWrite(LED_GREEN_PIN, LOW);
  digitalWrite(LED_BLUE_PIN, LOW);

  if (result.label == "good") {
    digitalWrite(LED_GREEN_PIN, HIGH);
    beep(1, 120);
  } else if (result.label == "defective") {
    digitalWrite(LED_RED_PIN, HIGH);
    beep(2, 120);
  } else {
    digitalWrite(LED_BLUE_PIN, HIGH);   // "not an egg" -- distinct from either real verdict
    beep(3, 80);
  }
}

void beep(int times, int durationMs) {
  for (int i = 0; i < times; i++) {
    digitalWrite(BUZZER_PIN, HIGH);
    delay(durationMs);
    digitalWrite(BUZZER_PIN, LOW);
    if (i < times - 1) delay(durationMs);
  }
}

void beepError() {
  digitalWrite(BUZZER_PIN, HIGH);
  delay(500);
  digitalWrite(BUZZER_PIN, LOW);
}
