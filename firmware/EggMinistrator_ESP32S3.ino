/*
  EggMinistrator -- ESP32-S3 firmware (load cell + LCD + LEDs + buzzer only)
  ----------------------------------------------------------------------------
  This board does NOT handle the camera. The camera is a regular USB webcam
  plugged into the laptop, which runs ai/inference/classify.py. This board's
  only job is the physical side: read the load cell, send the weight to the
  server, and show whatever verdict comes back on the LCD / LEDs / buzzer.

  The display is a 16x2 character LCD on I2C, NOT the SSD1306 OLED this
  sketch originally targeted. Two lines of sixteen characters is the whole
  canvas -- there is no graphics library and no text sizing.

  THE WEIGHT LEAVES OVER WI-FI, NOT OVER THE USB CABLE. The USB cable
  carries power only, and this is not a style preference: hardware/
  bill-of-materials.md is explicit that a USB *data* path makes this board a
  peripheral attached to a computer, which contradicts the paper's title and
  section 2.2. You can run this board off a power bank across the room and
  it behaves identically. Do not "simplify" it back onto serial.

  NOT COMPILE-TESTED -- I don't have this hardware or an Arduino toolchain
  to verify it on. Grounded in current documentation for the pin
  restrictions and library APIs, but treat it as a first draft to debug on
  real hardware, the way you would any code from any source you haven't
  run yet.

  ============================================================================
  REQUIRED LIBRARIES (Arduino IDE > Sketch > Include Library > Manage
  Libraries):
    - "HX711 Arduino Library" by Bogdan Necula
    - "LiquidCrystal I2C" by Frank de Brabander
    - "ArduinoJson" by Benoit Blanchon (v6.x)
  WiFi.h and HTTPClient.h ship with the esp32 board package -- nothing to
  install. The two Adafruit libraries the OLED needed are no longer required.
  Board: Tools > Board > ESP32 Arduino > pick your specific ESP32-S3 board
  (e.g. "ESP32S3 Dev Module"). Needs the "esp32" board package installed.

  ============================================================================
  BEFORE YOU FLASH: copy secrets.h.example to secrets.h and fill it in. That
  file holds the Wi-Fi password and the server address, and it is gitignored.
  Never put a real password in this file -- CONTRACT.md section 6.

  ============================================================================
  PROTOCOL -- see CONTRACT.md section 4.1, which is the authority. Three
  calls, in order:

    1. POST /api/inspections                  { "weight_g": 58.23 }
       -> server creates the row, replies     { "id": 41 }

    2. (the laptop POSTs the classifier output against id 41 -- not us)

    3. GET  /api/inspections/41/result        polled every 500 ms
       -> { "status": "pending" }             until step 2 lands
       -> { "label": "good", "confidence": 0.83 }

    label is one of: good, defective, not_an_egg   (Decision G spelling)

  Every request carries an X-Device-Key header. This board cannot log in as
  a user, so that header is how the server knows it is us.

  Calibrate LOADCELL_CALIBRATION_FACTOR the same way regardless of which
  ESP32 board you use -- see the comment on that constant below.
*/

#include <HX711.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <ArduinoJson.h>
#include <WiFi.h>
#include <HTTPClient.h>

#include "secrets.h"   // WIFI_SSID, WIFI_PASSWORD, SERVER_HOST, SERVER_PORT, DEVICE_KEY

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
#define LCD_SDA_PIN    8
#define LCD_SCL_PIN    9
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

// 0x27 is the usual address for the PCF8574 backpack on these modules; a
// good number of them are 0x3F instead. If the screen stays blank but the
// backlight is on, that is the first thing to try. An I2C scanner sketch
// settles it in a minute.
#define LCD_I2C_ADDRESS 0x27
LiquidCrystal_I2C lcd(LCD_I2C_ADDRESS, 16, 2);

// Declared up here, before handleResult() and showResult() use it. It was
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

long currentInspectionId = -1;                  // handed back by step 1
unsigned long lastPoll = 0;
const unsigned long POLL_INTERVAL_MS = 500;

// A hard ceiling on the "wait for the operator to take the egg off" loop.
// Without it a drifting load cell or an egg nobody removes hangs the board
// forever with no way out but the reset button.
const unsigned long REMOVAL_TIMEOUT_MS = 30000;

// ---------------------------------------------------------------------------
String baseUrl() {
  return String("http://") + SERVER_HOST + ":" + String(SERVER_PORT);
}

// ---------------------------------------------------------------------------
// Bounded, so a wrong password shows an error instead of hanging in setup().
bool connectWifi(unsigned long timeoutMs) {
  if (WiFi.status() == WL_CONNECTED) return true;

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < timeoutMs) {
    delay(250);
  }
  return WiFi.status() == WL_CONNECTED;
}

// ---------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);   // kept for debugging and load cell calibration only
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_RED_PIN, OUTPUT);
  pinMode(LED_GREEN_PIN, OUTPUT);
  pinMode(LED_BLUE_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(LED_RED_PIN, LOW);
  digitalWrite(LED_GREEN_PIN, LOW);
  digitalWrite(LED_BLUE_PIN, LOW);

  Wire.begin(LCD_SDA_PIN, LCD_SCL_PIN);
  // Unlike the OLED's begin(), LiquidCrystal_I2C::init() reports nothing back,
  // so a wrong address fails silently -- blank screen, lit backlight. See the
  // note on LCD_I2C_ADDRESS above.
  lcd.init();
  lcd.backlight();
  showMessage("Starting...");

  showMessage("Connecting WiFi");
  if (connectWifi(20000)) {
    Serial.print("Wi-Fi connected, IP ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("Wi-Fi FAILED -- check secrets.h");
    showMessage("WiFi failed\nCheck secrets.h");
    beepError();
  }

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
// Step 1. Returns true and sets currentInspectionId, or false on any failure.
bool postWeight(float grams) {
  if (!connectWifi(5000)) return false;

  HTTPClient http;
  http.begin(baseUrl() + "/api/inspections");
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Key", DEVICE_KEY);

  StaticJsonDocument<96> body;
  body["weight_g"] = grams;
  String payload;
  serializeJson(body, payload);

  int code = http.POST(payload);
  if (code != 200 && code != 201) {
    Serial.print("POST /api/inspections failed, HTTP ");
    Serial.println(code);
    http.end();
    return false;
  }

  StaticJsonDocument<128> reply;
  DeserializationError err = deserializeJson(reply, http.getString());
  http.end();
  if (err || !reply.containsKey("id")) {
    Serial.println("POST /api/inspections: no id in reply");
    return false;
  }

  currentInspectionId = reply["id"].as<long>();
  Serial.print("inspection id ");
  Serial.println(currentInspectionId);
  return true;
}

// ---------------------------------------------------------------------------
// Step 3. Asks once. Returns true only when a real verdict came back.
bool pollForResult(InspectionResultLocal &out) {
  if (currentInspectionId < 0) return false;
  if (WiFi.status() != WL_CONNECTED) return false;

  HTTPClient http;
  http.begin(baseUrl() + "/api/inspections/" + String(currentInspectionId) + "/result");
  http.addHeader("X-Device-Key", DEVICE_KEY);

  int code = http.GET();
  if (code != 200) {
    http.end();
    return false;
  }

  StaticJsonDocument<192> reply;
  DeserializationError err = deserializeJson(reply, http.getString());
  http.end();
  if (err) return false;

  // Still waiting on the laptop's classification -- not an error.
  if (!reply.containsKey("label")) return false;

  out.label = reply["label"].as<String>();
  out.confidence = reply["confidence"] | 0.0f;
  return true;
}

// ---------------------------------------------------------------------------
// Bounded wait for the operator to lift the egg off the platform. Bails out
// after REMOVAL_TIMEOUT_MS rather than blocking the board indefinitely.
void waitForEggRemoval() {
  unsigned long start = millis();
  while (readWeightGrams() > EGG_REMOVED_THRESHOLD_G) {
    if (millis() - start > REMOVAL_TIMEOUT_MS) {
      Serial.println("egg never removed -- giving up and re-arming");
      break;
    }
    delay(200);
  }
  digitalWrite(LED_RED_PIN, LOW);
  digitalWrite(LED_GREEN_PIN, LOW);
  digitalWrite(LED_BLUE_PIN, LOW);
  showMessage("Ready.\nPlace an egg.");
}

// ---------------------------------------------------------------------------
void handleResult(const InspectionResultLocal &result) {
  showResult(result);
  indicateResult(result);
  waitingForResult = false;
  currentInspectionId = -1;
  waitForEggRemoval();
}

// ---------------------------------------------------------------------------
void loop() {
  float weight = readWeightGrams();
  unsigned long now = millis();

  if (waitingForResult) {
    if (now - resultRequestedAt > RESULT_TIMEOUT_MS) {
      // The server never produced a verdict (laptop app not running? egg not
      // detected in frame?) -- don't leave the operator staring at a stale
      // "Sending weight" forever.
      showMessage("No response.\nTry again.");
      beepError();
      waitingForResult = false;
      currentInspectionId = -1;
      return;
    }

    if (now - lastPoll > POLL_INTERVAL_MS) {
      lastPoll = now;
      InspectionResultLocal result;
      if (pollForResult(result)) {
        handleResult(result);
      }
    }
    return;   // don't send more weight readings mid-inspection
  }

  if (weight < EGG_PRESENT_THRESHOLD_G) {
    delay(150);
    return;   // nothing on the platform yet
  }

  // An egg just showed up: send its weight, then wait for the verdict.
  if (now - lastWeightSend > WEIGHT_SEND_INTERVAL_MS) {
    showMessage("Egg detected.\nSending weight");   // 13 / 14 chars, fits 16x2
    lastWeightSend = now;

    if (postWeight(weight)) {
      waitingForResult = true;
      resultRequestedAt = now;
      lastPoll = now;
    } else {
      showMessage("Server error\nTry again.");
      beepError();
    }
  }
}

// ---------------------------------------------------------------------------
// Every message is at most two lines of sixteen characters. Call sites keep
// the original "\n" convention and this splits on it, so the message strings
// elsewhere in the file did not have to change.
//
// Anything past column 16 is CUT, not wrapped. A character LCD wraps a long
// line onto whichever row it feels like -- on many 16x2 modules row 0
// continues into row 2 of a 4-line address space, which shows up as nothing
// at all. Truncating is ugly on purpose; silent disappearance is worse.
void showMessage(const String &msg) {
  int split = msg.indexOf('\n');
  String top    = (split < 0) ? msg : msg.substring(0, split);
  String bottom = (split < 0) ? ""  : msg.substring(split + 1);

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(top.substring(0, 16));
  lcd.setCursor(0, 1);
  lcd.print(bottom.substring(0, 16));
}

// Verdict on the top row, confidence underneath. The longest label we can
// receive is "not_an_egg" at 10 characters, so it fits without truncating.
void showResult(const InspectionResultLocal &result) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(result.label.substring(0, 16));
  lcd.setCursor(0, 1);
  lcd.print("Conf: ");
  lcd.print(result.confidence * 100.0, 0);
  lcd.print("%");
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
