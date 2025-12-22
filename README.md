# Frencoin Mobile Wallet (Android)

Frencoin Mobile Wallet is a non-custodial Android wallet that bundles a Frencoin-aware Electrum client inside a Kivy user interface. If you are new to wallets, it simply means the app stores your private keys locally, connects to a trusted ElectrumX server for blockchain data, and lets you move coins without handing control to anyone else. If you are more experienced, you will be happy to know that everything happens client-side, transactions are signed with native `libsecp256k1`, and the Electrum stack runs in oneserver mode for consistent results.
<p align='center'>
<img width="225" height="500" alt="Frencoin Mobile Wallet Main Screen" src="https://github.com/user-attachments/assets/6f300e62-6926-4bd7-8e97-4e09115a467f" />
</p>

## Quick Overview

- **Self-custodial** – Your keys, your coins. The app stores private keys locally on your device, and no third party has access to your funds.
- **Electrum-powered** – Lightweight but proven networking layer.
- **Kivy UI layer** – Cross-platform Python UI toolkit makes layout tweaks straightforward.
- **Python-for-Android build** – Buildozer drives python-for-android (p4a) to create the APK with bundled Python modules and native libraries.

> **Important:** Set a strong password when prompted. This encrypts your wallet file and protects your funds if your device is lost, stolen, or backed up to cloud services. See the [Security Considerations](#security-considerations) section for details.

---

## Feature Tour
<p align='center'>
<img width="225" height="500" alt="Screenshot_20251212-220332" src="https://github.com/user-attachments/assets/b333d519-3f5e-490d-a32e-8bb27a22faf1" />
</p>

### Getting started & recovery
- Create a fresh 12-word recovery phrase or import an existing BIP39-compatible one.
- Backup flow immediately quizzes you on three random words so you don't lose your frens.
- Wallet files are stored using Electrum’s wallet database format.

### Sending & receiving funds
- Receive tab shows the current address in a non-editable field, includes a one-tap copy button, and confirms the copy in the status bar to avoid guessing.
- Send form manages the soft keyboard so the important fields stay visible; long-press actions provide paste and clear shortcuts on the address entry.
- A confirmation dialog summarizes destination, amount, and fee tier. Fee control includes presets (Slow / Normal / Fast / Extreme) plus a custom slider for advanced use, along with the “subtract fee from amount” toggle.
- Successful broadcasts display a pop-up containing the transaction ID and a copy button for quick sharing.

### Awareness & feedback
- The balance label refreshes every 15 seconds and clearly shows when the wallet is syncing.
- History view highlights incoming funds in green and outgoing funds in red, includes abbreviated TXIDs, and keeps the ten most recent entries handy.
- Tapping a timestamp reveals the full date/time; tapping a TXID launches the Frencoin block explorer in your browser.
- Manual refresh button triggers a background sync when you want data right now.

### Security & privacy
- In-app password encrypts the wallet file and must be entered before signing, viewing the seed, or changing security settings. **Strongly recommended** to protect against device loss/theft and cloud backups.
- Brute-force protection locks password entry after repeated failed attempts, with escalating cooldown periods that persist across app restarts.
- Clipboard is automatically cleared 60 seconds after copying sensitive data (addresses, transaction IDs).
- Menu flow allows password changes, fee preference tweaks, and seed review (password-gated) at any time.
- Ships with prebuilt `libsecp256k1.so` for the supported ABIs so signatures are handled by hardened native code.

### Quality-of-life polish
- Status line shows Electrum connectivity (server, sync state, errors) so you immediately know if something is wrong.
- Dialogs and popups keep inputs visible by managing scroll areas and keyboard focus.
- Long-press helpers and snack-bar confirmations reduce accidental edits or missed actions.

---

## Repository Layout

| Path | Purpose |
| --- | --- |
| `main.py` | App entry point: Kivy UI definitions, Electrum wiring, send/receive flows, and status updates. |
| `electrum/` | Vendored Electrum fork tuned for Frencoin parameters and default server. |
| `buildozer.spec` | Buildozer configuration (requirements list, Android arch list, packaged assets, permissions). |
| `p4a-recipes/` | Custom python-for-android recipes (e.g., KawPow, X16R/V2). |
| `libs/` | ABI-specific folders holding the prebuilt `libsecp256k1.so` binaries. |
| `bin/` | Output APKs from Buildozer runs (ignored when not needed). |
| `p4a_310_env/` | Example Python 3.10 virtual environment (kept for reference but not meant for sharing). |

---

## Build From Source

You can build on Linux, macOS, or Windows (via WSL2). The steps below assume CPython 3.10 because python-for-android currently targets it most reliably.

### 1. Install prerequisites

**Common requirements**
- Python 3.10 with `venv`
- Java 17 or newer
- Git, zip/unzip, compiler toolchain (`make`, `gcc`, `pkg-config`, `autoconf`, `automake`, `libtool`)
- Android SDK + NDK + platform tools (Buildozer will fetch these on first run)
- Around 8 GB of free disk space for Buildozer caches and Android tools

**Ubuntu/Debian**
```bash
sudo apt update
sudo apt install git python3.10 python3.10-venv python3-pip \
    openjdk-17-jdk zip unzip make gcc pkg-config autoconf automake libtool \
    libffi-dev libssl-dev
```

**macOS (Homebrew)**
```bash
brew install python@3.10 git openjdk autoconf automake libtool pkg-config \
    sdl2 sdl2_image sdl2_mixer sdl2_ttf gstreamer
```

On macOS you may also need:
```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 17)
```

### 2. Clone and set up a virtual environment

```bash
git clone https://github.com/<you>/frencoin_mobile_wallet.git
cd frencoin_mobile_wallet_3
python3.10 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install "cython<3" "buildozer>=1.5.0"
```

> Each developer should keep their own `.venv/` out of version control. The sample `p4a_310_env/` folder is just an example of what **not** to commit.

### 3. Make sure native libraries exist

The wallet expects `libsecp256k1.so` inside `libs/<abi>/` for every ABI you target (`armeabi-v7a`, `arm64-v8a`, etc.). Fresh clones already contain prebuilt binaries. If you change secp256k1 or add a new ABI:

1. Follow `libs/README.md` to cross-compile the library with the Android NDK.
2. Drop the resulting `.so` under the correct `libs/<abi>/` folder.
3. Rerun Buildozer so the new binary is bundled.

### 4. Build a debug APK

```bash
buildozer -v android debug
```

- The first run downloads SDK/NDK packages and puts them in `.buildozer/`.
- Buildozer parses `buildozer.spec`, installs Python requirements via p4a, compiles native modules, and packages the APK.
- When the build completes you’ll find the APK under `bin/frencoinwallet-<version>-<arch>-debug.apk`.

Deploy to a connected device (ADB-enabled) with:

```bash
buildozer android debug deploy run logcat
```

### 5. Build a release APK (optional)

```bash
buildozer android release
```

Sign the resulting `*.apk` or `*.aab` with your own keystore, then run `zipalign`/`apksigner` as you would for any Android release. Never commit the keystore or passwords.

### 6. Clean up & troubleshoot

- `buildozer android clean` removes previous artifacts without wiping the SDK.
- `buildozer appclean` resets the entire python-for-android distribution cache.
- If compilation fails, confirm the Java version is 17+, the virtual environment is active, and system build tools are installed (Xcode Command Line Tools on macOS, `build-essential` on Linux).
- When switching Python versions, recreate the virtual environment so cached wheels under `.buildozer/` do not mix interpreters.

---

## Security Considerations

### Set a password

When you create or restore a wallet, the app prompts you to set a password. **This is strongly recommended.** The password encrypts your wallet file using strong cryptography, which means:

- If someone gains physical access to your device, they cannot extract your seed phrase without the password.
- If your device is backed up to Google Drive or other cloud services (enabled by default on most Android devices), the backup will contain an encrypted wallet file that is useless without your password.
- If you skip setting a password, your wallet file is stored unencrypted. Anyone with access to your device or its backups could steal your funds.

### Android backups and cloud storage

Android may automatically back up app data to Google Drive. This app allows such backups so that your wallet can survive a device reset or migration. However, this means your wallet file could be stored on Google's servers.

- **With a password:** The backed-up wallet file is encrypted. Google (or anyone who compromises your Google account) cannot access your funds without your wallet password.
- **Without a password:** The backed-up wallet file is unencrypted. Anyone with access to your Google account backups could extract your seed phrase and steal your funds.

If you prefer to disable cloud backups entirely, you can do so in your Android settings under "Backup" or by using ADB to disable backup for this specific app.

### Your seed phrase is everything

Your 12-word seed phrase can restore your wallet on any compatible device. Treat it like cash:

- Write it down on paper and store it securely offline.
- Never share it with anyone, including "support" staff.
- Never enter it on a website or send it over the internet.
- The app will never ask you to "verify" your seed phrase after initial setup (except during the backup quiz immediately after creation).

### Other security features

- **Brute-force protection:** After several wrong password attempts, the app enforces escalating cooldown periods (1 minute, then 3 minutes, then 5+ minutes). This state persists across app restarts.
- **Clipboard clearing:** When you copy an address or transaction ID, the clipboard is automatically cleared after 60 seconds to prevent other apps from reading sensitive data.
- **Secure file permissions:** Wallet files are created with restrictive permissions (owner read/write only) to prevent other apps from accessing them.

---

## FAQ

### Why keep Electrum inside the repo?

Shipping a vendored Electrum copy guarantees Frencoin network tweaks, default servers, and UX changes stay in sync with the app. Upstream updates can be merged intentionally, tested, and released without unpredictable external dependencies.

### Can I point at another ElectrumX server?

Yes. `main.py` wires `SimpleConfig` to `35.208.59.201:50002:s` in oneserver mode. Change the host, port, or SSL flag there to point to your own infrastructure or to fall back to server auto-discovery.

### What is `p4a_310_env/` doing here?

It is a snapshot of a developer’s macOS virtual environment. It cannot be reused on other machines because it contains absolute paths and platform-specific binaries. Treat it as an example of what to ignore: everyone should create their own `.venv/` and keep it local.

### Do I need a specific operating system?

Linux and macOS are both supported, and Windows users can build inside WSL2. Pick whichever environment has stable USB debugging and Android tooling for you. The important part is running CPython 3.10 with Java 17 and enough disk space for SDK downloads.

---

Happy hacking, and thanks for helping bring Frencoin to Android!
