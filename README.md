# Enhanced Scanning Console (ESC)

The **Enhanced Scanning Console (ESC)** is a robust, containerized web application designed to capture, store, and manage barcode scans in real-time. Built specifically with hardware barcode scanners (like the Zebra DS22) in mind, it provides a seamless, synced dashboard across multiple devices.

## Features

- **Real-Time Synchronization**: Instantly pushes new scans and deletions to all connected browser clients via WebSockets.
- **Smart Duplicate Handling**: Scanning the same item multiple times automatically increments its count and bubbles it to the top of the history list.
- **Hardware Integration**: Can receive scans directly via USB (`/dev/input` via `evdev` for Linux/Raspberry Pi) or safely fallback to an auto-focusing hidden input field on any browser.
- **Data Persistence**: Uses a lightweight SQLite database safely stored in a Docker volume to survive reboots.
- **Premium UI**: Dark mode, glassmorphic design built with React. Includes one-click copy and CSV export capabilities. 
- **Multi-Architecture**: Built natively for both `x86_64` (Windows/Mac/Linux PCs) and `arm64` (Raspberry Pi/ARM servers).

## Quick Start (Production)

To deploy the application, you can use the pre-built Docker image (`leraptor65/enhancedscanningconsole:latest`) which is compiled for both standard PCs and ARM devices like the Raspberry Pi.

1. Ensure you have Docker and Docker Compose installed on your host system.
2. Pull down the `compose.yml` file from this repository to your computer/server.
3. Run the application in the background:
```bash
docker compose up -d
```
4. Navigate to `http://<YOUR_SERVER_IP>:8000` from any device on your network!

## Local Development (Building from Source)

If you want to edit the code and build the container locally from scratch on your own machine, a separate compose file is provided.

1. Clone this repository.
2. Run the development build command to compile the React code and launch the Python backend locally:
```bash
docker compose -f compose.dev.yml up --build -d
```

### Changing the Theme
The background gradient and UI colors are managed via native CSS variables. Open `frontend/src/index.css` and change the `--bg-gradient` or `--accent` hex colors to theme the application differently. Re-run the local build command to bake your changes into a new container.

## Troubleshooting

- **Scanner not working natively on Raspberry Pi**: If you have the USB scanner directly plugged into the Pi server but it's not recognizing scans when you look away from the browser, make sure you have the `/dev/input:/dev/input:ro` volume mapped, and add `privileged: true` under `services` in your `compose.yml` to grant Docker permission to read USB event streams.
- **Browser capturing fails**: If you click away and the scanner stops registering on the web app fallback, simply click anywhere on the dark background. The app is programmed to automatically recapture your keyboard focus for the scanner!
