Daywell OS 1.0

Daywell OS is a 64-bit Raspberry Pi OS derivative for a single-user touchscreen tablet. It uses the upstream Linux kernel, boot firmware, drivers, and Debian package repositories. A local Wayland session runs labwc and Chromium in kiosk mode. The home screen is stored on the SD card and can start offline.

## Try the interface

**[Open the public Daywell demo](https://ask-afk.github.io/Git_OS/)**

The demo page, stylesheet, and JavaScript files returned HTTP 200 when checked on November 22, 2026. Browser interaction verification in this environment was blocked by a certificate error.

In the demo, try Family Photos and its next/previous buttons, mark a reminder, play Relaxing music, and try a simulated family call. Reset demo clears the current conversation and returns home. Reminder checkmarks remain stored in your browser.

The demo displays sample data and explains that password protection and Agey's local model require the installed server. To try those features on your own computer, clone this repository and start its local server. Python 3.11 or later is required. The server uses the Python standard library.

```sh
git clone https://github.com/Ask-afk/Git_OS.git
cd Git_OS
python3 server.py
```

Open http://127.0.0.1:8787/. On your first visit, create a local password of at least eight characters. Agey also requires the Ollama setup described below.

## Publish the demo

1. Push the demo workflow and source changes to the main branch.
2. Open this repository's Settings → Pages and select GitHub Actions as the build source.
3. Under Actions, run Publish interface demo, or wait for its push-triggered run to succeed.
4. Open the workflow's deployment URL and test the photo album. Use that verified URL in Crescent's playable-link field.

To test the static export locally, run `python3 scripts/build-demo.py`, then `python3 -m http.server 8080 --directory public-demo`. Open http://localhost:8080/.

## Build and install a Raspberry Pi image

Build an image using the instructions under **Customize and rebuild** before following the installation steps. Physical boot on the intended Raspberry Pi remains unverified.

1. Use a Raspberry Pi 4 or 5 with a connected touchscreen, audio output, and a suitable power supply. The interface targets a 1280 × 800 landscape display. Prepare a spare microSD card of at least 16 GB.
2. Open Raspberry Pi Imager. Select **Use custom** and choose **Daywell-OS-1.0-arm64.img.xz**. Select the spare card. Writing the image erases the selected card.
3. Insert the card into the Pi and power it on. Allow the first boot to expand the filesystem. The local tablet account starts automatically and opens Daywell's password setup. Create a password of at least eight characters, then unlock **My home**.
4. For internet radio, connect Ethernet or configure Wi-Fi through the base image's cloud-init network configuration before first boot. The boot partition includes a commented network-config file. The clock uses the system time and time zone. Configure the timezone through cloud-init or the administrator account.

The supplied tablet account is called daywell. It uses automatic login on the physical display and has no configured password or sudo membership. Daywell's password protects the local web interface, not the Linux account or files on the SD card. For maintenance, provision a separate administrator account through the boot partition's cloud-init user-data before the first boot. Use a different username. Physical keyboard access to another virtual terminal is available for that administrator.

The distribution retains upstream first-boot firmware and boot artwork. The Daywell name appears in the home screen, Linux OS identity, console login banner, and message of the day.

## Using the tablet

- **Call Family** opens three example contacts. Confirming a call starts a simulation. A real video service and contact provisioning would be needed for live calls.
- **Family Photos** browses three local sample photos. Replace them in ui/assets and edit the captions in ui/app.js to personalize the album.
- **Daily Reminders** stores each day's checkmarks in the local Chromium profile. Tap again to clear a checkmark. The included tasks are examples.
- **Radio & Music** streams WQXR Classical and BBC World Service News when reachable. Relaxing plays an included offline chord progression. Volume controls adjust playback within the app.
- **Help / SOS** displays instructions for seeking urgent help by telephone. The image does not dial or alert a caregiver.
- **Talk to Agey** sends the current conversation to an Ollama model running on the same tablet. The conversation stays in browser memory and clears when Chromium closes. Agey can make mistakes and cannot contact anyone or provide emergency service.
- **Lock** ends the local web session. Five minutes without touch or keyboard input also locks the interface.
- Weather is visibly labeled sample data. The date and time come from the device.
- **Go back** returns from every secondary screen.

Each interactive control uses a single tap. Button feedback uses Web Audio. Optional spoken button labels can be enabled in ui/brand.js if Chromium has an installed speech voice. Larger or narrower layouts can scroll when needed.

## Customize and rebuild

The source package includes the complete tablet interface, Linux startup files, local server, and image builder. For a desktop preview, run `python3 server.py` and open `http://127.0.0.1:8787/`. The first visit creates a local password. The tablet runs this server automatically; Chromium opens its loopback address.

1. Edit the quoted TABLET_BRAND value in ui/brand.js. The builder uses the same name for the OS identity and login banner. Update the sunrise emblem in ui/index.html and palette in ui/style.css as desired.
2. On a Linux build host, install Python 3.11 or later, e2fsprogs, curl, and xz-utils. Allow 12 GB of free space. The builder operates on image files using debugfs and requires no root access.
3. In the extracted source directory, run the following. Substitute your preferred output filename.

```sh
curl -fL -o raspberry-pi-os.img.xz https://downloads.raspberrypi.com/raspios_arm64/images/raspios_arm64-2026-10-06/2026-10-06-raspios-trixie-arm64.img.xz
python3 build-image.py raspberry-pi-os.img.xz Daywell-OS-custom.img.xz
```

The builder verifies the official base image SHA-256, installs the UI and server into /opt/daywell, and sets the multi-user boot target. A first-boot systemd service prepares the local user. The Daywell server runs as that user and listens only on 127.0.0.1:8787. A tty1 login launches the Wayland compositor and its fullscreen browser. A supervisor restarts the browser if it exits. The builder checks the resulting ext4 filesystem before writing the compressed image.

## Set up local Agey

Agey requires Ollama and a model on the tablet. They are not included in the image because the model is a separate, large download. Using the separate administrator account, follow [Ollama's Linux install instructions](https://ollama.com/download/linux), then run:

```sh
ollama pull gemma3:1b
curl -fsS http://127.0.0.1:11434/api/tags
```

The default model is [gemma3:1b](https://ollama.com/library/gemma3:1b). To use another installed local model, set `DAYWELL_OLLAMA_MODEL` in a systemd override for `daywell-server.service` and restart that service. Keep Ollama bound to loopback. Model responses on a Pi, especially a 4, may be slow. The chat screen displays a clear error if Ollama or the model is unavailable.

## Local access and security limits

The password is stored as a salted scrypt hash in `/var/lib/daywell/auth.json` with owner-only permissions. The server gates the UI and Agey API, accepts requests only on loopback, limits login guesses, and uses an HttpOnly, SameSite session cookie. Sessions expire after 30 minutes of server inactivity; the browser locks after five minutes without input. Authentication and chat requests stay on the device's loopback network unless Ollama has been configured to use a remote model.

This is an application lock, not full disk encryption or an OS login. Anyone with physical access to the SD card or a shell as `daywell` or an administrator can read local data, bypass the browser lock, or reset its password. The Chromium profile also stores reminder checkmarks without encryption. The local HTTP connection has no TLS; it is intended only for the same device. For stronger protection against physical access, add OS login and disk encryption, and disable automatic login.

## Verification scope

The local server has automated checks for setup, login, guarded files, lockout, logout, and the Ollama bridge. Physical boot, touchscreen calibration, speaker output, internet station availability, Ollama performance, and video hardware acceleration require testing on the intended Pi and display.

## Included assets

The interface illustrations and offline audio are included in the source. The contact portraits and album are illustrative stock photographs from Unsplash. Upstream OS components retain their existing licenses and copyright notices, including the package documentation in /usr/share/doc.

