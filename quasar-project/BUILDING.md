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

Open the application, enter the host's LAN address and Flask port, and connect.
On the host itself, `localhost` works. Check login, task creation/retrieval, and
five-second refresh between computers. The default connection-screen port is
50000; enter the actual port used by Flask.

The Electron main process limits API requests to the selected host and `/api/`
paths. Chromium web security remains enabled. The existing manual connection
uses HTTP, so traffic is not encrypted. These unsigned prototype builds still
need HTTPS with certificate verification and signing for distribution.

Build outputs and dependencies are ignored by Git. Do not commit them.
