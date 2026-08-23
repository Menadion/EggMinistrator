#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <HX711.h>

// =====================================================
// PIN DEFINITIONS
// =====================================================

// RGB MODULE
#define RED_LED    25
#define GREEN_LED  26
#define ORANGE_LED 27

// HX711 LOAD CELL
#define HX711_DT  32
#define HX711_SCK 33

// LCD I2C
#define LCD_SDA 21
#define LCD_SCL 22

// BUZZER
#define BUZZER  4


// =====================================================
// OBJECTS
// =====================================================

LiquidCrystal_I2C lcd(0x27, 16, 2);

HX711 scale;


// =====================================================
// LOAD CELL CALIBRATION
// =====================================================

// Your tested calibration factor
float calibration_factor = 698.0;


// =====================================================
// SYSTEM VARIABLES
// =====================================================

bool eggDetected = false;
bool inspectionStarted = false;
bool waitingForAI = false;

float eggWeight = 0.0;


// =====================================================
// SETUP
// =====================================================

void setup() {

  // -------------------------------------------------
  // SERIAL
  // -------------------------------------------------

  Serial.begin(115200);


  // -------------------------------------------------
  // RGB MODULE
  // -------------------------------------------------

  pinMode(RED_LED, OUTPUT);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(ORANGE_LED, OUTPUT);


  // -------------------------------------------------
  // BUZZER
  // -------------------------------------------------

  pinMode(BUZZER, OUTPUT);

  digitalWrite(BUZZER, LOW);


  // -------------------------------------------------
  // LCD
  // -------------------------------------------------

  Wire.begin(LCD_SDA, LCD_SCL);

  lcd.init();
  lcd.backlight();


  // -------------------------------------------------
  // HX711
  // -------------------------------------------------

  scale.begin(HX711_DT, HX711_SCK);

  scale.set_scale(calibration_factor);


  // -------------------------------------------------
  // STARTUP
  // -------------------------------------------------

  setGreen();

  lcd.clear();

  lcd.setCursor(0, 0);
  lcd.print("Egg Inspector");

  lcd.setCursor(0, 1);
  lcd.print("Starting...");

  delay(2000);


  // -------------------------------------------------
  // CHECK HX711
  // -------------------------------------------------

  if (scale.is_ready()) {

    Serial.println("HX711 detected.");

  } else {

    Serial.println("WARNING: HX711 not ready!");

  }


  // -------------------------------------------------
  // TARE
  // -------------------------------------------------

  lcd.clear();

  lcd.setCursor(0, 0);
  lcd.print("Initializing");

  lcd.setCursor(0, 1);
  lcd.print("Scale...");

  delay(2000);


  // Make sure the platform is empty
  scale.tare();


  // -------------------------------------------------
  // READY
  // -------------------------------------------------

  showReady();

}


// =====================================================
// MAIN LOOP
// =====================================================

void loop() {

  // ===================================================
  // CHECK AI RESULT
  // ===================================================

  checkAIResult();


  // ===================================================
  // DETECT EGG USING LOAD CELL
  // ===================================================

  if (!waitingForAI) {

    float currentWeight = getWeight();


    // -----------------------------------------------
    // NO EGG
    // -----------------------------------------------

    if (currentWeight < 5.0) {

      if (eggDetected) {

        eggDetected = false;
        inspectionStarted = false;

      }

      setGreen();

      showReady();

      delay(500);

      return;
    }


    // -----------------------------------------------
    // EGG DETECTED
    // -----------------------------------------------

    if (!eggDetected) {

      eggDetected = true;

      setRed();

      lcd.clear();

      lcd.setCursor(0, 0);
      lcd.print("EGG DETECTED");

      lcd.setCursor(0, 1);
      lcd.print("Measuring...");

      Serial.println("EGG:DETECTED");

      delay(1500);

    }


    // =================================================
    // START INSPECTION
    // =================================================

    if (!inspectionStarted) {

      inspectionStarted = true;


      // ---------------------------------------------
      // GET FINAL WEIGHT
      // ---------------------------------------------

      eggWeight = getWeight();


      // Prevent negative values
      if (eggWeight < 0) {
        eggWeight = 0;
      }


      // ---------------------------------------------
      // DISPLAY WEIGHT
      // ---------------------------------------------

      lcd.clear();

      lcd.setCursor(0, 0);
      lcd.print("WEIGHT:");

      lcd.setCursor(8, 0);
      lcd.print(eggWeight, 1);
      lcd.print("g");


      lcd.setCursor(0, 1);
      lcd.print("Quality Check");


      // ---------------------------------------------
      // SEND WEIGHT TO COMPUTER
      // ---------------------------------------------

      Serial.print("WEIGHT:");
      Serial.println(eggWeight, 1);


      delay(2000);


      // ---------------------------------------------
      // START AI INSPECTION
      // ---------------------------------------------

      setOrange();


      lcd.clear();

      lcd.setCursor(0, 0);
      lcd.print("QUALITY CHECK");

      lcd.setCursor(0, 1);
      lcd.print("SCANNING...");


      // Tell Python webcam program to capture
      Serial.println("CAPTURE");


      waitingForAI = true;

    }

  }


  delay(100);

}


// =====================================================
// GET WEIGHT
// =====================================================

float getWeight() {

  if (!scale.is_ready()) {

    Serial.println("HX711 not ready!");

    return 0.0;

  }


  // Average 10 readings
  float weight = scale.get_units(10);


  return weight;

}


// =====================================================
// CHECK AI RESULT
// =====================================================

void checkAIResult() {

  if (Serial.available()) {

    String result = Serial.readStringUntil('\n');

    result.trim();


    Serial.print("Received: ");
    Serial.println(result);


    // -----------------------------------------------
    // GOOD
    // -----------------------------------------------

    if (result == "QUALITY:GOOD") {

      showGoodResult();

    }


    // -----------------------------------------------
    // BAD
    // -----------------------------------------------

    else if (result == "QUALITY:BAD") {

      showBadResult();

    }

  }

}


// =====================================================
// READY
// =====================================================

void showReady() {

  lcd.clear();

  lcd.setCursor(0, 0);
  lcd.print("PLACE EGG");

  lcd.setCursor(0, 1);
  lcd.print("READY");

}


// =====================================================
// GOOD RESULT
// =====================================================

void showGoodResult() {

  waitingForAI = false;


  // Green = Good
  setGreen();


  lcd.clear();

  lcd.setCursor(0, 0);
  lcd.print("QUALITY: GOOD");


  lcd.setCursor(0, 1);
  lcd.print(eggWeight, 1);
  lcd.print("g ACCEPTED");


  // One beep
  beep();


  delay(3000);


  lcd.clear();

  lcd.setCursor(0, 0);
  lcd.print("RESULT SAVED");

  lcd.setCursor(0, 1);
  lcd.print("Remove Egg");


  delay(1000);

}


// =====================================================
// BAD RESULT
// =====================================================

void showBadResult() {

  waitingForAI = false;


  // Red = Bad
  setRed();


  lcd.clear();

  lcd.setCursor(0, 0);
  lcd.print("QUALITY: BAD");


  lcd.setCursor(0, 1);
  lcd.print(eggWeight, 1);
  lcd.print("g CHECK");


  // Two beeps
  beep();

  delay(200);

  beep();


  delay(3000);


  lcd.clear();

  lcd.setCursor(0, 0);
  lcd.print("RESULT SAVED");

  lcd.setCursor(0, 1);
  lcd.print("Remove Egg");


  delay(1000);

}


// =====================================================
// RGB - GREEN
// =====================================================

void setGreen() {

  // GREEN ON
  digitalWrite(GREEN_LED, HIGH);

  // RED OFF
  digitalWrite(RED_LED, LOW);

  // BLUE CHANNEL OFF
  digitalWrite(ORANGE_LED, LOW);

}


// =====================================================
// RGB - RED
// =====================================================

void setRed() {

  // RED ON
  digitalWrite(RED_LED, HIGH);

  // GREEN OFF
  digitalWrite(GREEN_LED, LOW);

  // BLUE OFF
  digitalWrite(ORANGE_LED, LOW);

}


// =====================================================
// RGB - ORANGE
// =====================================================

void setOrange() {

  // RED = ON
  digitalWrite(RED_LED, HIGH);

  // GREEN = PARTIAL
  analogWrite(GREEN_LED, 80);

  // BLUE = OFF
  digitalWrite(ORANGE_LED, LOW);

}


// =====================================================
// BUZZER
// =====================================================

void beep() {

  digitalWrite(BUZZER, HIGH);

  delay(300);

  digitalWrite(BUZZER, LOW);

}