# Daywell OS

Daywell is a Raspberry Pi tablet project for older adults. The idea is to make everyday things easier to find, with large buttons for photos, reminders, music, and family contacts.

[Try the demo](https://ask-afk.github.io/Git_OS/)

## What you can try

The demo lets you look through a sample photo album, check off reminders, play music, and try a simulated family call.

There’s also an Agey chat screen. To get replies from Agey, you need to run Daywell locally with Ollama installed.

The photos and contacts are examples. Calls are simulated, the weather is sample data, and the Help button shows instructions for getting help by telephone.

## Run it locally

You need Python 3.11 or newer.

```sh
git clone https://github.com/Ask-afk/Git_OS.git
cd Git_OS
python3 server.py
```

Open http://127.0.0.1:8787/ in your browser. The first time you open it, you’ll be asked to create a password of at least eight characters.

## Set up Agey

Install and start Ollama on the same computer as Daywell, then download the model:

```sh
ollama pull gemma3:1b
```

With Ollama running, open Talk to Agey in Daywell. The chat shows an error if the model is unavailable. Replies may be slow on a Raspberry Pi.

The default model is gemma3:1b. You can choose another installed model with the DAYWELL_OLLAMA_MODEL environment variable. On the Pi, set it in an override for daywell-server.service and restart the service.

## Change things

Most of the interface is in the `ui` folder.

- `brand.js` contains the project name.
- `style.css` controls the colors, fonts, and layout.
- `app.js` contains the contacts, captions, reminders, and screen behavior.
- `assets` holds the photos and offline music.

To preview the public demo on your computer:

```sh
python3 scripts/build-demo.py
python3 -m http.server 8080 --directory public-demo
```

Then open http://localhost:8080/.

## Raspberry Pi version

Daywell uses Raspberry Pi OS, with a local Python server and Chromium running fullscreen. The interface is designed around a 1280 × 800 touchscreen.

To build an image, use a Linux computer with Python 3.11 or newer, `e2fsprogs`, `curl`, and `xz-utils`. Allow at least 12 GB of free space.

```sh
curl -fL -o raspberry-pi-os.img.xz https://downloads.raspberrypi.com/raspios_arm64/images/raspios_arm64-2026-10-06/2026-10-06-raspios-trixie-arm64.img.xz
python3 build-image.py raspberry-pi-os.img.xz Daywell-OS-custom.img.xz
```

Use Raspberry Pi Imager’s **Use custom** option to write the resulting image to a spare microSD card of at least 16 GB. Writing the image erases that card.

The startup files are configured to open Daywell automatically. Physical boot, touchscreen calibration, audio, and Agey’s performance still need testing on the intended Pi. Ollama and its model need installing separately.

## Passwords and privacy

The local server stores a salted password hash and limits failed login attempts. It listens only on the device’s loopback address.

The screen locks after five minutes without input. Reminder checkmarks stay in the browser profile, and Agey’s conversation stays in browser memory.

The password protects the web interface. Someone with access to the Linux account or SD card can still access local files. The Pi’s tablet account logs in automatically, so maintenance should use a separate administrator account.

## Tests

Run the server tests with:

```sh
python3 -m unittest discover -s tests
```

These cover password setup, login, protected files, lockout, logout, and the connection to Ollama.

## Where Codex helped

I started Daywell to make a Raspberry Pi tablet easier for older adults to use. OpenAI Codex helped extensively with the interface, Linux startup files and image builder. This project builds on that AI-assisted starting point.

## Credits

The sample photos are from Unsplash. The interface illustrations and offline audio are included in the source.

Daywell uses Raspberry Pi OS and its kernel, firmware, drivers, and packages. Those components keep their original licenses and copyright notices.
````
