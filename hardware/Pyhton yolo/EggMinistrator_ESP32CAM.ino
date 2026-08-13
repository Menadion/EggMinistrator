/*
  EggMinistrator -- ESP32-CAM firmware
  ------------------------------------
  Captures one candling photo and one weight reading per egg, sends both to
  the local classification server (egg_server.py) in a single HTTP request,
  and shows the result locally: OLED text, a red/green LED, and a buzzer.

  NOT COMPILE-TESTED. I don't have ESP32 hardware or an Arduino toolchain
  available to me, so unlike the Python side of this project, this file is
  a careful first draft grounded in current documentation and standard
  library APIs -- not verified-working code. Expect to debug it on real
  hardware. Read every "// TODO" and "CHECK:" comment below before flashing.

  ============================================================================
  REQUIRED LIBRARIES (Arduino IDE > Sketch > Include Library > Manage
  Libraries -- search each name and install):
    - "HX711 Arduino Library" by Bogdan Necula
    - "Adafruit SSD1306" by Adafruit
    - "Adafruit GFX Library" by Adafruit (SSD1306 depends on this)
    - "ArduinoJson" by Benoit Blanchon (v6.x)
  Board: Tools > Board > ESP32 Arduino > "AI Thinker ESP32-CAM"
  Also needs the "esp32" board package installed (Boards Manager).

  ============================================================================
  BEFORE YOU FLASH -- fill these in:
*/
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* SERVER_HOST   = "192.168.1.100";   // your laptop/server's LAN IP -- NOT the ESP32's IP
const uint16_t SERVER_PORT = 5000;
const char* SERVER_PATH   = "/inspect";

// HX711 calibration factor. You MUST calibrate this yourself -- it depends
// on your specific load cell and can't be guessed. Standard procedure:
//   1. Flash a minimal sketch that just prints scale.get_units(10) in a
//      loop with no weight on the platform, after scale.tare().
//   2. Place a known weight (e.g. a 50g reference weight, or anything you
//      can weigh precisely elsewhere) and note the raw reading.
//   3. LOADCELL_CALIBRATION_FACTOR = raw_reading / known_weight_grams
//   4. Re-flash this file with that value and confirm scale.get_units()
//      now reports the correct grams for a few different test weights.
// See: https://randomnerdtutorials.com/esp32-load-cell-hx711/ for the full
// walkthrough -- the wiring differs (see the wiring guide in this project),
// but the calibration procedure is identical.
float LOADCELL_CALIBRATION_FACTOR = 2280.0;    // TODO: replace after calibrating

// ============================================================================

#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <HX711.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <ArduinoJson.h>

// -- Peripheral pins -- see the wiring guide for why these specific pins.
// Deliberately avoids GPIO 0 (camera clock + boot-mode), GPIO 12 (documented
// to cause boot failures with pulled-up peripherals), and GPIO 16 (shared
// with PSRAM -- documented to crash the camera mid-capture if used).
#define HX711_DT_PIN   13
#define HX711_SCK_PIN  14
#define OLED_SDA_PIN   15
#define OLED_SCL_PIN   2
#define BUZZER_PIN     4    // shares the onboard flash LED -- it'll flicker faintly, harmless
#define LED_RED_PIN    3    // this is the UART RX pin -- see note in setup()
#define LED_GREEN_PIN  1    // this is the UART TX pin -- see note in setup()

// -- Camera pins (AI-Thinker ESP32-CAM). Do not change these -- they are
// fixed by the board's hardware wiring, not a design choice.
#define PWDN_GPIO_NUM   32
#define RESET_GPIO_NUM  -1
#define XCLK_GPIO_NUM    0
#define SIOD_GPIO_NUM   26
#define SIOC_GPIO_NUM   27
#define Y9_GPIO_NUM     35
#define Y8_GPIO_NUM     34
#define Y7_GPIO_NUM     39
#define Y6_GPIO_NUM     36
#define Y5_GPIO_NUM     21
#define Y4_GPIO_NUM     19
#define Y3_GPIO_NUM     18
#define Y2_GPIO_NUM      5
#define VSYNC_GPIO_NUM  25
#define HREF_GPIO_NUM   23
#define PCLK_GPIO_NUM   22

// Egg presence / removal thresholds, in grams. Tune these once your load
// cell is calibrated and you've seen what an empty platform reads (should
// be ~0, but a little sensor noise is normal).
const float EGG_PRESENT_THRESHOLD_G = 20.0;
const float EGG_REMOVED_THRESHOLD_G = 15.0;

HX711 scale;
Adafruit_SSD1306 display(128, 64, &Wire, -1);

struct InspectionResult {
  String label;       // "good", "defective", or "not_egg"
  float confidence;
  bool ok;             // false if the request failed for any reason
  String errorMessage;
};

// ---------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  // NOTE: LED_RED_PIN/LED_GREEN_PIN are the UART RX/TX pins. Once wired to
  // LEDs you will not see Serial output (or be able to send serial input)
  // during normal operation. This is fine for day-to-day use; if you need
  // to debug over Serial, temporarily disconnect the two LED wires first.
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_RED_PIN, OUTPUT);
  pinMode(LED_GREEN_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(LED_RED_PIN, LOW);
  digitalWrite(LED_GREEN_PIN, LOW);

  Wire.begin(OLED_SDA_PIN, OLED_SCL_PIN);
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    // CHECK: 0x3C is the usual SSD1306 I2C address, but some 0.96" boards
    // ship on 0x3D -- if the display stays blank, try that instead.
    Serial.println("OLED not found at 0x3C -- check wiring / try address 0x3D");
  }
  display.setTextColor(SSD1306_WHITE);
  showMessage("Starting...");

  scale.begin(HX711_DT_PIN, HX711_SCK_PIN);
  scale.set_scale(LOADCELL_CALIBRATION_FACTOR);
  scale.tare();  // zero the scale -- make sure the platform is empty when this runs

  if (!setupCamera()) {
    showMessage("Camera init\nfailed. Check\nwiring, restart.");
    beepError();
    while (true) delay(1000);   // nothing useful to do without a camera
  }

  connectWiFi();
  showMessage("Ready.\nPlace an egg.");
}

// ---------------------------------------------------------------------------
bool setupCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  // The egg is stationary during capture (per the project doc), so there's
  // no motion-blur reason to keep resolution low -- use PSRAM if present
  // for a sharper image, which matters more for detecting fine cracks.
  if (psramFound()) {
    config.frame_size = FRAMESIZE_VGA;   // 640x480
    config.jpeg_quality = 12;            // lower number = higher quality
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_QVGA;  // 320x240 -- PSRAM-less boards can't do more reliably
    config.jpeg_quality = 15;
    config.fb_count = 1;
  }

  return esp_camera_init(&config) == ESP_OK;
}

// ---------------------------------------------------------------------------
void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  showMessage("Connecting\nWiFi...");
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 40) {   // ~20s timeout
    delay(500);
    attempts++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WiFi connected, IP: ");
    Serial.println(WiFi.localIP());
  } else {
    showMessage("WiFi failed.\nRetrying in loop().");
  }
}

// ---------------------------------------------------------------------------
float readWeightGrams() {
  if (!scale.is_ready()) return 0.0;
  return scale.get_units(5);   // average of 5 samples -- smooths sensor noise
}

// ---------------------------------------------------------------------------
void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
    delay(1000);
    return;
  }

  float weight = readWeightGrams();
  if (weight < EGG_PRESENT_THRESHOLD_G) {
    delay(200);   // nothing meaningful on the platform yet -- keep polling
    return;
  }

  showMessage("Egg detected.\nCapturing...");
  delay(400);   // let the platform/reading settle before the "real" weight read
  weight = readWeightGrams();

  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    showMessage("Capture failed.\nRetrying.");
    beepError();
    delay(1000);
    return;
  }

  InspectionResult result = sendInspection(fb, weight);
  esp_camera_fb_return(fb);

  if (!result.ok) {
    showMessage("Server error:\n" + result.errorMessage);
    beepError();
    delay(2000);
    return;
  }

  showResult(result, weight);
  indicateResult(result);

  // Wait for the operator to remove the egg before watching for the next one
  while (readWeightGrams() > EGG_REMOVED_THRESHOLD_G) {
    delay(200);
  }
  digitalWrite(LED_RED_PIN, LOW);
  digitalWrite(LED_GREEN_PIN, LOW);
  showMessage("Ready.\nPlace an egg.");
  delay(300);
}

// ---------------------------------------------------------------------------
InspectionResult sendInspection(camera_fb_t *fb, float weightGrams) {
  InspectionResult result;
  result.ok = false;

  HTTPClient http;
  String url = String("http://") + SERVER_HOST + ":" + String(SERVER_PORT) + SERVER_PATH;
  http.begin(url);
  http.setTimeout(8000);   // classification + network round trip -- NFR-01 budgets 3s for the model itself

  String boundary = "EggMinistratorBoundary7331";
  http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);

  // Weight and image go in ONE multipart request, matching the project
  // doc's "single HTTP request containing the image and the weight
  // reading, so that each inspection is recorded as one transaction".
  String head = "--" + boundary + "\r\n"
                "Content-Disposition: form-data; name=\"weight\"\r\n\r\n" +
                String(weightGrams, 2) + "\r\n"
                "--" + boundary + "\r\n"
                "Content-Disposition: form-data; name=\"image\"; filename=\"egg.jpg\"\r\n"
                "Content-Type: image/jpeg\r\n\r\n";
  String tail = "\r\n--" + boundary + "--\r\n";

  size_t totalLen = head.length() + fb->len + tail.length();
  uint8_t *body = (uint8_t *)malloc(totalLen);
  if (!body) {
    result.errorMessage = "Out of memory";
    http.end();
    return result;
  }
  size_t pos = 0;
  memcpy(body + pos, head.c_str(), head.length());   pos += head.length();
  memcpy(body + pos, fb->buf, fb->len);               pos += fb->len;
  memcpy(body + pos, tail.c_str(), tail.length());    pos += tail.length();

  int httpCode = http.POST(body, totalLen);
  free(body);

  if (httpCode != 200) {
    result.errorMessage = "HTTP " + String(httpCode);
    http.end();
    return result;
  }

  String payload = http.getString();
  http.end();

  // Expected response from egg_server.py:
  //   {"label": "good", "confidence": 0.83}
  StaticJsonDocument<256> doc;
  DeserializationError err = deserializeJson(doc, payload);
  if (err) {
    result.errorMessage = "Bad response";
    return result;
  }

  result.label = doc["label"].as<String>();
  result.confidence = doc["confidence"] | 0.0;
  result.ok = (result.label.length() > 0);
  if (!result.ok) result.errorMessage = "No label in response";
  return result;
}

// ---------------------------------------------------------------------------
void showMessage(const String &msg) {
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println(msg);
  display.display();
}

void showResult(const InspectionResult &result, float weightGrams) {
  display.clearDisplay();
  display.setTextSize(2);
  display.setCursor(0, 0);
  display.println(result.label);
  display.setTextSize(1);
  display.setCursor(0, 20);
  display.print("Conf: ");
  display.print(result.confidence * 100.0, 0);
  display.println("%");
  display.setCursor(0, 34);
  display.print("Weight: ");
  display.print(weightGrams, 1);
  display.println(" g");
  display.display();
}

// ---------------------------------------------------------------------------
// FR-15: "Indicate the classification result at the inspection station
// through a visual indicator and an audible signal."
void indicateResult(const InspectionResult &result) {
  digitalWrite(LED_RED_PIN, LOW);
  digitalWrite(LED_GREEN_PIN, LOW);

  if (result.label == "good") {
    digitalWrite(LED_GREEN_PIN, HIGH);
    beep(1, 120);
  } else if (result.label == "defective") {
    digitalWrite(LED_RED_PIN, HIGH);
    beep(2, 120);
  } else {
    // "not an egg" -- blink both, distinct from either verdict
    for (int i = 0; i < 3; i++) {
      digitalWrite(LED_RED_PIN, HIGH);
      digitalWrite(LED_GREEN_PIN, HIGH);
      delay(150);
      digitalWrite(LED_RED_PIN, LOW);
      digitalWrite(LED_GREEN_PIN, LOW);
      delay(150);
    }
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
  // A longer, distinct tone for "something's wrong" vs. a normal result beep
  digitalWrite(BUZZER_PIN, HIGH);
  delay(500);
  digitalWrite(BUZZER_PIN, LOW);
}
