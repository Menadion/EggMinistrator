# Setting up a machine that has never run EggMinistrator

Written 2026-08-24, when it became clear the demo might run on a laptop where none of this
had ever been installed.

Four processes have to come up in order — MySQL, the backend, the classifier listener, the
dashboard — and each depends on the one before it. `run-eggministrator.bat` does that for you
once the pieces below exist. This file is about getting the pieces to exist.

🔴 **Start step 5 first and let it run while you do everything else.** TensorFlow is several hundred
megabytes. Every other step here takes minutes; that one can take an evening on a slow connection,
and the classifier cannot run without it.

## 1. Install what is not in the repo

| | Why |
|---|---|
| **Git** | to clone at all |
| **Node.js LTS** | the backend and the dashboard both run on it |
| **Python 3.11+** | the classifier, the capture tool, the stub server |
| **XAMPP** | for MySQL. Nothing else in XAMPP is used — **do not start Apache.** It is not needed here and can collide with other projects on the same machine |
| **Arduino IDE** | only if you are flashing the board |

## 2. Clone

```
git clone https://github.com/Menadion/EggMinistrator.git
cd EggMinistrator
```

## 3. Database

Start **MySQL only** from the XAMPP Control Panel, then from the repo root:

```
C:\xampp\mysql\bin\mysql.exe -u root < database\schema.sql
C:\xampp\mysql\bin\mysql.exe -u root eggministrator < database\sample-data.sql
C:\xampp\mysql\bin\mysql.exe -u root eggministrator < database\seed-five-month-demo-data.sql
C:\xampp\mysql\bin\mysql.exe -u root eggministrator < database\extend-demo-data-through-july-25.sql
C:\xampp\mysql\bin\mysql.exe -u root eggministrator < database\rebalance-five-month-demo-sizes.sql
```

Four things that are easy to get wrong here:

- 🔴 **`schema.sql` DROPS every table before recreating them.** On a fresh machine that is
  exactly what you want. On a machine that already has data, it destroys it. Check which one
  you have before running it.
- **Skip `database/migrations/` entirely.** All three files are already folded into
  `schema.sql` — verified 2026-08-24. Running them afterwards errors on columns that exist.
- **`sample-data.sql` seeds the `users` table.** Skip it and there is no way to log in.
- The three demo-data scripts rebuild the dashboard's historical charts. Skip them and
  everything works but every chart is empty.

XAMPP's root account has no password by default, hence no `-p`. Add it if yours does.

## 4. Node dependencies

```
cd backend    && npm install && cd ..
cd dashboard  && npm install && cd ..
```

## 5. Python — start this one FIRST, in its own window

```
py -m venv .venv
.venv\Scripts\pip install -r ai\requirements.txt
```

## 6. `backend\.env`

```
copy backend\.env.example backend\.env
```

Then fill in the values. **`.env` is gitignored and never arrives with the clone**, which is
why a working machine has one and a fresh one does not.

🔴 **`DEVICE_API_KEY` must be byte-identical to the one in
`firmware\EggMinistrator_ESP32\secrets.h`.** If they differ, every station call answers 401
and the symptom looks like a dead board rather than a wrong key.

The backend loads this file via `node --env-file=.env`, so **it will refuse to start if
`.env` is missing** rather than starting and failing every request. That is deliberate: for
several weeks it did the latter, and nobody noticed because all testing went through the stub
server.

## 7. Let the launcher find what this list forgot

```
run-eggministrator.bat
```

It checks each prerequisite and stops at the first missing one, naming the exact path and the
command that fixes it. Then it brings up MySQL → backend → listener → dashboard in order,
the three servers as tabs of one Windows Terminal window (or one window each where
`wt.exe` is missing), and opens the browser. `stop` closes the tabs it empties.

```
run-eggministrator.bat --no-listener    leaves the webcam free for ai\capture.py
stop-eggministrator.bat                 station down, MySQL left running
stop-eggministrator.bat listener        frees the webcam, everything else keeps running
```

`stop` leaves MySQL running on purpose: XAMPP's MySQL is often shared with other work, and
stopping a database to shut down an egg station would take that with it.

Log in at **http://localhost:5173**.

## 8. The board

`firmware\EggMinistrator_ESP32\secrets.h` ships as `FILL-ME-IN`. Set the Wi-Fi credentials,
`SERVER_PORT` to `3001`, and `SERVER_HOST` to the IP address the launcher prints at the very
top of its output — that is what it prints it for, and it changes whenever the network does.

- The board and the laptop must be on the **same 2.4 GHz network**. The classic ESP32 has no
  5 GHz radio, and the board here is a classic ESP32-D0WD-V3, not an S3.
- If the board cannot reach the server, the usual cause is Windows Firewall blocking inbound
  `node.exe` or `python.exe`. Allow them on private networks.

## What "working" looks like

| | |
|---|---|
| MySQL | port 3306 answering |
| Backend | `Eggministrator backend listening at http://localhost:3001` |
| Listener | `Model loaded: ...`, then `Listening at http://127.0.0.1:3001` |
| Dashboard | Vite on 5173, and the browser opens by itself |

The listener needs a trained model at `ai\models\egg.keras`. Without one the launcher says so
and skips it; everything else still comes up.
