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
// Pins. REMAPPED 2026-08-15 for a CLASSIC ESP32, not the S3.
//
// The board is an ESP32-D0WD-V3, confirmed by reading it with
// firmware/board-id/board-id.ino rather than from the can, which is marked
// only "ESP32-32X" -- a reseller marking, not an Espressif part number.
//
// The earlier map was written for an ESP32-S3 and four of its pins were
// unusable here: on a classic ESP32, GPIO6 to GPIO11 are wired to the
// integrated SPI flash, and the LCD (8, 9), the buzzer (10) and the red LED
// (11) all sat in that range. Driving them crashes the chip. GPIO12 was also
// a poor choice -- it is MTDI, and held high at boot it selects a 1.8 V flash
// voltage and the board may not start at all.
//
// Avoided on this chip: GPIO6-11 (SPI flash), GPIO0/2/12/15 (strapping),
// GPIO1/3 (UART0, in use by the serial monitor), GPIO34-39 (input only, no
// output driver). GPIO16/17 are also skipped so that this map works unchanged
// on a WROVER module, where those two carry PSRAM.
// ⚠️ HX711 on 4/5 because J has that wired and reading correctly on the real
// board, and both are legitimate on a classic ESP32. An earlier pass moved
// them to 32/33 on paper; verified hardware beats a tidier theory.
#define HX711_DT_PIN   4
#define HX711_SCK_PIN  5
#define LCD_SDA_PIN   21   // the classic ESP32 I2C default pair, so stock
#define LCD_SCL_PIN   22   // wiring guides for this board apply as written
#define BUZZER_PIN    25
#define LED_RED_PIN   26
#define LED_GREEN_PIN 27
#define LED_BLUE_PIN  23   // only used for the "not an egg" indicator -- see indicateResult()

// ✅ CONFIRMED 2026-08-16: three LEDs exist. J found a third beyond the red
// and green, so each of the three verdicts gets its own colour and the BOM
// now reads 3 pieces. CONTRACT and the paper were right all along and need
// no correction.
//
// Set this false if the third LED is ever lost or reassigned: indicateResult()
// then signals "not an egg" by blinking red and green together, which is still
// visibly distinct from either verdict and still satisfies FR-15's visual half.
#define HAS_BLUE_LED true

// ⚠️ J currently has his two LEDs on GPIO12 and GPIO13. 13 is fine. 12 is
// MTDI: held HIGH at boot it selects a 1.8 V flash voltage and the board may
// not start at all. His works because his code drives it LOW, but that is one
// stray pull-up away from an unbootable board, so the pins above move it clear.

// HX711 calibration factor -- MUST be calibrated for your specific load
// cell, the same procedure regardless of which ESP32 board drives it:
//   1. Flash a minimal sketch that prints scale.get_units(10) in a loop
//      with nothing on the platform, right after scale.tare().
//   2. Place a known weight (anything you can weigh precisely elsewhere)
//      and note the raw reading.
//   3. LOADCELL_CALIBRATION_FACTOR = raw_reading / known_weight_grams
//   4. Re-flash with that value; confirm get_units() reports correctly
//      for a couple of different test weights before trusting it.
// ✅ CALIBRATED 2026-08-16 by J, on the load cell this project owns.
// He measured a raw difference of 503206 - 458939 = 44267 counts for a known
// 60 g weight, giving 44267 / 60 = 737.8, and settled on 735.25 in testing.
// An egg then read 58.6 g, which is a plausible egg rather than a coincidence.
// Re-calibrate if the load cell, the HX711 or the egg holder ever changes --
// the factor describes that whole mechanical assembly, not just the cell.
float LOADCELL_CALIBRATION_FACTOR = 735.25;

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

  // Taken from J's bench sketch, and it fixes a real defect here. tare() calls
  // wait_ready() internally, which spins until the HX711's DOUT pin goes low.
  // With the amplifier unwired or on the wrong pins that never happens and
  // setup() hangs forever -- no serial past this point, no HTTP, nothing. It
  // reads as a dead board rather than a wiring fault. Ask first, with a bound.
  if (!scale.wait_ready_timeout(3000)) {
    Serial.println("ERROR: HX711 not responding -- check DT/SCK wiring and power");
    showMessage("HX711 error\nCheck wiring");
    beepError();
    // Deliberately does not continue. Every weight from here would be garbage,
    // and a station silently reporting nonsense is worse than one that stops.
    while (true) delay(1000);
  }

  scale.set_scale(LOADCELL_CALIBRATION_FACTOR);

  showMessage("Taring...\nEmpty the plate");
  delay(2000);      // give the operator a moment to take anything off
  scale.tare(20);   // 20 readings rather than the default; steadier zero

  showMessage("Ready.\nPlace an egg.");
}

// ---------------------------------------------------------------------------
float readWeightGrams() {
  if (!scale.is_ready()) return 0.0;
  return scale.get_units(5);
}

// ---------------------------------------------------------------------------
// The weight that actually gets sent. A single get_units() reading taken the
// instant an egg lands is still settling, so this waits for the mechanical
// bounce to die down and then averages. From J's bench sketch, where it was
// the difference between a stable number and one that drifted a gram either
// way while you watched it.
float settledWeightGrams() {
  delay(800);   // let the egg stop rocking before measuring anything

  const int readings = 20;
  float total = 0;
  for (int i = 0; i < readings; i++) {
    float grams = scale.get_units(1);
    if (grams < 0) grams = 0;   // a hair below zero is noise, not a negative egg
    total += grams;
    delay(30);
  }
  return total / readings;
}

// ---------------------------------------------------------------------------
// ⚠️ TEMPORARY, AND IT IS A SECOND COPY OF SOMETHING THE SERVER OWNS.
//
// Size grading belongs to the server: CONTRACT decision 4, implemented by
// findSizeGrade() against the size_grades table. This exists only so the board
// can show something useful on the LCD while running standalone on the bench,
// before the laptop half of section 4.1 exists.
//
// DELETE THIS the moment the board is getting real verdicts back from the
// server. Two copies of a grading rule is two rules, and the one on the LCD
// will eventually disagree with the one on the dashboard in front of somebody.
//
// The bands are PNS/BAFS 321:2021, matching database/sample-data.sql exactly.
// J's bench sketch used the USDA sizes instead (Small 42.52, Medium 49.61,
// Large 56.70, X-Large 63.79, Jumbo 70.87), which is a different national
// standard: a 58.6 g egg is Medium under PNS and Large under USDA. The paper
// cites PNS, so PNS wins here.
String localSizeGrade(float grams) {
  if (grams <  45.0) return "Pewee";
  if (grams <  55.0) return "Small";
  if (grams <  60.0) return "Medium";
  if (grams <  65.0) return "Large";
  if (grams <  70.0) return "Extra Large";
  return "Jumbo";
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

  // An egg just showed up: settle, measure properly, then send.
  if (now - lastWeightSend > WEIGHT_SEND_INTERVAL_MS) {
    showMessage("Egg detected.\nMeasuring...");
    lastWeightSend = now;

    // The trigger reading above only had to clear a 20 g threshold. It is not
    // the measurement -- the egg is still settling when it crosses that line.
    // This is the number that goes in the database and drives the size grade,
    // so it is worth the extra second.
    float finalWeight = settledWeightGrams();

    // Bench aid only: shows a grade before the server has answered. Goes away
    // with localSizeGrade() once the laptop half of section 4.1 exists.
    Serial.print("Final weight: ");
    Serial.print(finalWeight, 2);
    Serial.print(" g, local grade ");
    Serial.println(localSizeGrade(finalWeight));

    showMessage("Sending weight");

    if (postWeight(finalWeight)) {
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
    // "not an egg". With three LEDs this gets its own colour. With two, blue
    // does not exist, so fall back to blinking red and green together -- still
    // visibly different from either verdict, which is the whole requirement,
    // rather than silently doing nothing and looking like a crash.
    if (HAS_BLUE_LED) {
      digitalWrite(LED_BLUE_PIN, HIGH);
    } else {
      for (int i = 0; i < 3; i++) {
        digitalWrite(LED_RED_PIN, HIGH);
        digitalWrite(LED_GREEN_PIN, HIGH);
        delay(150);
        digitalWrite(LED_RED_PIN, LOW);
        digitalWrite(LED_GREEN_PIN, LOW);
        delay(150);
      }
    }
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
