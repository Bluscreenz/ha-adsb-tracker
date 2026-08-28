# ADS-B Aircraft Tracker for Home Assistant

Track a specific aircraft (by tail number / registration) using your own
**local** ADS-B receiver (dump1090, readsb, tar1090, ultrafeeder, PiAware, etc.),
entirely inside Home Assistant — no cloud service, no FlightAware/ADSBExchange
account needed.

What you get:

- A config flow so you enter your ADS-B server's IP once, via the Home
  Assistant UI (defaults pre-filled for `192.168.7.52`).
- An **Options** menu (UI, no YAML) to add or remove tracked tail numbers
  at any time.
- One `binary_sensor` per tracked tail number that turns **on** whenever
  that aircraft is currently being received, with attitude/speed/squawk/
  distance as attributes.
- An event (`adsb_tracker_aircraft_seen`) fired the instant an aircraft is
  first seen, plus a ready-to-import automation blueprint that sends a
  push notification to your phone via the Home Assistant companion app.

Everything runs as local polling against your own receiver's JSON feed —
nothing here talks to the internet at runtime.

---

## 1. Requirements

Your ADS-B receiver at `192.168.7.52` needs to expose the standard
`aircraft.json` endpoint that dump1090/readsb/tar1090-family software
produces. This is already true for most common setups:

- **ultrafeeder / adsb.im images** — usually `http://192.168.7.52:8080/data/aircraft.json`
- **tar1090** — usually `http://192.168.7.52/tar1090/data/aircraft.json` or `:8080/data/aircraft.json`
- **dump1090-fa (PiAware/SkyAware)** — usually `http://192.168.7.52:8080/skyaware/data/aircraft.json` or `http://192.168.7.52/skyaware/data/aircraft.json`
- **plain dump1090-mutability** — usually `http://192.168.7.52:8080/data/aircraft.json`

**Check yours before installing:** open the URL in a browser or run:

```bash
curl http://192.168.7.52:8080/data/aircraft.json
```

If that 404s, try the paths above until you find the working one — you'll
enter the exact port/path in the setup form.

Also check whether the JSON includes an `"r"` field (registration/tail
number) per aircraft — tar1090 and ultrafeeder normally include this via
their aircraft database. If your feed only has `"flight"` (callsign) and
`"hex"` (ICAO address), you can still track an aircraft by entering its
callsign instead of its tail number — the integration falls back to
matching on callsign, then raw ICAO hex, automatically.

---

## 2. Installing the integration

### Option A — Manual copy (simplest, no GitHub needed)

1. Copy the `custom_components/adsb_tracker` folder from this package into
   your Home Assistant config directory, so you end up with:
   ```
   <config>/custom_components/adsb_tracker/__init__.py
   <config>/custom_components/adsb_tracker/manifest.json
   <config>/custom_components/adsb_tracker/config_flow.py
   <config>/custom_components/adsb_tracker/coordinator.py
   <config>/custom_components/adsb_tracker/binary_sensor.py
   <config>/custom_components/adsb_tracker/const.py
   <config>/custom_components/adsb_tracker/strings.json
   <config>/custom_components/adsb_tracker/translations/en.json
   ```
   (If you use the Samba/File Editor/VS Code add-on, `<config>` is the
   folder that already contains `configuration.yaml`.)
2. Copy the `blueprints/automation/adsb_tracker/notify_on_seen.yaml` file
   into `<config>/blueprints/automation/adsb_tracker/notify_on_seen.yaml`.
3. **Restart Home Assistant** (Settings → System → Restart).

### Option B — HACS custom repository

HACS's default store only lists integrations submitted to its public
index, so a private/custom one like this is added as a **custom
repository**. This still installs and updates over your home network/
internet just for the *install* step — the integration itself only ever
talks to your local ADS-B server at runtime.

1. Push the contents of this package to your own GitHub repository (e.g.
   `github.com/<you>/ha-adsb-tracker`), keeping the same folder layout
   (`custom_components/adsb_tracker/...`, `hacs.json` at the repo root).
2. In Home Assistant, open **HACS**.
3. Click the **⋮** menu (top right) → **Custom repositories**.
4. Add your repo URL, category **Integration**, click **Add**.
5. Search for "ADS-B Aircraft Tracker" in HACS, open it, click **Download**.
6. **Restart Home Assistant.**
7. (Optional) In HACS, go to the repository page → **⋮** → the blueprint
   isn't auto-installed by HACS integrations, so also copy
   `blueprints/automation/adsb_tracker/notify_on_seen.yaml` manually into
   `<config>/blueprints/automation/adsb_tracker/` as in step 2 of Option A,
   or import it via the link method in section 4 below.

---

## 3. Setting up the connection and tail numbers (all via UI)

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **ADS-B Aircraft Tracker** and select it.
3. Fill in the form:
   - **Host / IP address**: `192.168.7.52` (pre-filled)
   - **Port**: the port for your feed (default `8080`)
   - **JSON path**: the path for your feed (default `/data/aircraft.json`)
   - **Poll interval**: how often to check, in seconds (default `15`)
   - **Receiver latitude / longitude**: optional — enter your antenna's
     coordinates to get a `distance_nm` attribute on each sensor.
4. Click **Submit**. The integration is now connected.
5. On the new integration card, click **Configure**.
6. Choose **Add a tail number**, enter e.g. `N12345`, optionally give it a
   friendly name (e.g. "Dad's Cessna"), and submit.
7. Repeat "Configure → Add a tail number" for as many aircraft as you want
   to track. Use "Remove a tail number" the same way to stop tracking one.
8. Each tail number appears as its own entity, e.g.
   `binary_sensor.n12345` — no restart needed, entities update live.

---

## 4. Getting alerts on your phone

The binary sensor turning "on" is the signal — wire it to a notification
using the included blueprint:

1. Go to **Settings → Automations & Scenes → Blueprints → Import Blueprint**.
2. Paste in the raw URL to `notify_on_seen.yaml` if you hosted it on
   GitHub, **or** just place the file as described in section 2 and it
   will already appear in the blueprint list after a restart — click
   **Create Automation** from it directly.
3. Pick the **Aircraft binary sensor** (e.g. `binary_sensor.n12345`).
4. Enter your **Notify service** — find it under Settings → Devices &
   Services → your phone's entry (companion app), or Developer Tools →
   Actions, searching "notify". It looks like `notify.mobile_app_your_phone`.
5. Save. Repeat once per tracked aircraft (or per phone).

You'll now get a push notification like:

> ✈️ Aircraft spotted
> N12345 (N12345) is now being received. Altitude: 4500 ft. Speed: 140 kt.

If you'd rather build your own automation instead of using the blueprint,
you can trigger on:
- the binary sensor's state changing to `on`, or
- the event `adsb_tracker_aircraft_seen` (fires once per "newly seen"
  transition, with `tail_number`, `flight`, `altitude_ft`, etc. as event
  data) — useful if you want one automation covering all tracked aircraft.

---

## 5. Entity attributes

Each `binary_sensor.<tail_number>` exposes, when the aircraft is currently
seen:

| Attribute           | Description                                  |
|---------------------|-----------------------------------------------|
| `tail_number`       | The tail number you entered                   |
| `flight`             | Callsign currently being broadcast            |
| `hex`                | ICAO 24-bit address                           |
| `altitude_ft`        | Barometric altitude                           |
| `ground_speed_kt`    | Ground speed in knots                         |
| `track_deg`          | Track/heading in degrees                      |
| `latitude` / `longitude` | Current position, if being reported       |
| `squawk`             | Transponder squawk code                       |
| `distance_nm`        | Distance from your receiver (if lat/lon set)  |

---

## 6. Troubleshooting

- **Integration won't set up / shows "unavailable"**: double-check the
  host/port/path against section 1 — try the URL in a browser first.
- **Sensor never turns on even when you know the plane is nearby**: your
  feed may not populate the `r` (registration) field. Try entering the
  aircraft's **callsign** as the tracked value instead, or check
  `curl http://192.168.7.52:8080/data/aircraft.json | grep -i <hex>` to see
  what fields are actually present for that aircraft.
- **Logs**: add this to `configuration.yaml` for verbose debugging, then
  restart:
  ```yaml
  logger:
    default: warning
    logs:
      custom_components.adsb_tracker: debug
  ```

---

## Notes on "local only"

This integration only ever makes outbound HTTP requests to the host/port/
path you configure (your own ADS-B server). It does not call any cloud
API, and works fully with Home Assistant's internet connection disabled,
as long as your ADS-B server and phone/companion app can still reach your
Home Assistant instance on your LAN. The only network step outside your
LAN is the optional one-time HACS *download* step in Option B — remove
that dependency entirely by using Option A (manual copy).
