# HomeField desktop builds

Flask must be started manually on the host. These packages contain only the
Electron/Vue frontend; clients do not run a backend or store a database.

Install dependencies and build from `quasar-project/`:

```sh
npm ci
cd src-electron
npm ci
cd ..
npm run build:mac
npm run build:windows
```

Run builds one at a time. Output is under `dist/electron/`:

- `darwin-arm64/Packaged/HomeField-darwin-arm64/HomeField.app`: Apple Silicon Macs.
- `win32-x64/Packaged/HomeField-win32-x64/HomeField.exe`: 64-bit Windows. Copy the **entire**
  `HomeField-win32-x64` folder, keeping the executable and its supporting files
  together. This is an unpacked application, not an installer.

For an Intel Mac, run `npx quasar build -m electron -T darwin -A x64`.

Install the host dependencies with `python -m pip install -r backend/requirements.txt`
and start Flask from the repository root with `python backend/app.py`.
This startup advertises HomeField on the local network; `flask run` does not.

Open the application and choose your host from **Available hosts**. It searches
for four seconds on opening the connection screen; **Search again** repeats the
search. Multiple network interfaces may show more than one address for a host.
You still choose the host explicitly before login; discovery never sends passwords
or tokens and does not establish trust in a server or its certificate.

If no host appears, enter the host's LAN address and Flask port manually.
On the host itself, `localhost` works. Check login, task creation/retrieval, and
five-second refresh between computers. The default connection-screen port is
50000; enter the actual port used by Flask.

Allow local-network access if your operating system prompts. Discovery uses mDNS
(UDP 5353); Flask uses TCP 50000. Both machines must be on the same reachable LAN.
School/guest Wi-Fi may block multicast or communication between devices; manual
entry helps only when normal TCP access is allowed. After the host changes networks
or its IP changes, restart Flask to advertise its current addresses, then search
again. Browser-only builds retain manual entry because discovery runs in Electron.

Discovery tests: `python -m pytest -q backend/tests/test_discovery.py` and,
from `quasar-project/`, `node --test src-electron/tests/discovery.test.js`.

The Electron main process limits API requests to the selected host and `/api/`
paths. Chromium web security remains enabled. The existing manual connection
uses HTTP, so traffic is not encrypted. These unsigned prototype builds still
need HTTPS with certificate verification and signing for distribution.

Build outputs and dependencies are ignored by Git. Do not commit them.
