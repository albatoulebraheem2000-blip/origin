# Origin AI Android — Python/Kivy

This folder contains a native Python/Kivy Android client for the Origin AI API. It is not a WebView and does not bundle the React site.

## Run on a desktop for development

1. Install Python 3.11 (recommended for current Kivy/Buildozer tooling).
2. Create and activate a virtual environment.
3. Run `pip install -r requirements.txt`.
4. Start the Python Origin server from the repository root with `python main.py`.
5. Run `python main.py`.

Enter the computer's current LAN address on the first screen, for example `http://192.168.1.100:3000`. No address is compiled into the app: a successful address is saved locally and can be changed later from Profile. The phone and computer must be on the same Wi-Fi/hotspot.

The authenticated session cookie is stored in the Android app's private data directory, so restarting the app keeps the session until logout or server-side expiry. On an empty database, the app automatically opens the secure first-owner setup screen; enter the setup token shown/configured on the Python server when required.

The client supports account setup/login, assets, editing and deletion, AI scan API calls, maintenance, market list/unlist, transfers (accept/reject/cancel), public passports, and the admin summary.

Arabic text uses the bundled Noto Sans Arabic font under the SIL Open Font License (`assets/fonts/OFL.txt`).

## Build an APK

Buildozer is supported on Linux. On Windows, use WSL2 (Ubuntu) or a Linux build machine:

```text
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip python3-venv autoconf libtool pkg-config zlib1g-dev libncurses5-dev cmake libffi-dev libssl-dev
python3 -m venv .venv
source .venv/bin/activate
pip install buildozer cython
cd mobile_python
buildozer android debug
```

The APK will be created under `mobile_python/bin/`. Install it on the phone, start the Origin server with LAN hosting, then enter its Network IP in the app. The LAN build explicitly enables clear-text HTTP through `android_application_attributes.xml`.

Android blocks clear-text HTTP by default in some configurations. Buildozer/python-for-android normally permits the local API when `usesCleartextTraffic` is enabled; for production, host the API behind HTTPS and update the saved server address.
