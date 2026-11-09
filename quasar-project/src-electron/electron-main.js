import { app, BrowserWindow, ipcMain } from 'electron'
import path from 'node:path'
import os from 'node:os'
import {
  registerQuasarRuntime,
  resolveElectronAssetsPath
} from '#q-app/electron/main'

// needed in case process is undefined under Linux
const platform = process.platform || os.platform()

async function createWindow() {
  // This window runs only the frontend. Flask is started separately on the host.
  const mainWindow = new BrowserWindow({
    icon: resolveElectronAssetsPath('icons/icon.png'), // Windows and Linux
    width: 1000,
    height: 600,
    useContentSize: true,
    webPreferences: {
      // Keep Vue isolated from Node.js; privileged actions use the preload bridge.
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      // https://v2.quasar.dev/quasar-cli-vite/developing-electron-apps/electron-preload-script
      preload: path.join(import.meta.dirname, 'electron-preload.cjs')
    }
  })

  // Until a host is selected, API requests are blocked. This resets on reopening.
  let backendOrigin = null
  const contents = mainWindow.webContents
  // Keep remote pages from replacing the bundled frontend or opening new windows.
  contents.setWindowOpenHandler(() => ({ action: 'deny' }))
  contents.on('will-navigate', event => event.preventDefault())

  // The renderer can select a backend, but cannot access Electron or Node APIs.
  // Replace the previous handler when macOS recreates a closed window.
  ipcMain.removeHandler('homefield:select-host')
  ipcMain.handle('homefield:select-host', (event, address) => {
    // Accept requests only from this window's main frame, not embedded frames.
    if (event.sender !== contents || event.senderFrame !== contents.mainFrame) {
      throw new Error('Invalid connection request')
    }
    const url = new URL(address)
    // Store an origin only: credentials, paths, and query strings do not belong
    // in the host setting. HTTP remains available for the current LAN prototype.
    if (
      !['http:', 'https:'].includes(url.protocol) ||
      url.username ||
      url.password ||
      url.pathname !== '/' ||
      url.search ||
      url.hash
    ) {
      throw new Error('Invalid host address')
    }
    backendOrigin = url.origin
  })

  // Packaged file pages have a null origin. Scope their API access to the
  // selected host instead of disabling Chromium's web security or Flask CORS.
  contents.session.webRequest.onBeforeRequest((details, callback) => {
    // Electron classifies both fetch and XMLHttpRequest API calls as "xhr".
    if (details.resourceType === 'xhr') {
      const url = new URL(details.url)
      callback({
        cancel:
          url.origin !== backendOrigin || !url.pathname.startsWith('/api/')
      })
      return
    }
    callback({})
  })
  contents.session.webRequest.onHeadersReceived((details, callback) => {
    const url = new URL(details.url)
    if (
      details.resourceType === 'xhr' &&
      url.origin === backendOrigin &&
      url.pathname.startsWith('/api/')
    ) {
      const headers = { ...details.responseHeaders }
      // Replace any server CORS allowance locally for this selected API only.
      // Flask's configuration and the responses other clients receive are unchanged.
      for (const key of Object.keys(headers)) {
        if (key.toLowerCase().startsWith('access-control-allow-'))
          delete headers[key]
      }
      callback({
        responseHeaders: {
          ...headers,
          'Access-Control-Allow-Origin': [
            import.meta.env.QUASAR_DEV
              ? new URL(import.meta.env.QUASAR_APP_URL).origin
              : 'null'
          ],
          'Access-Control-Allow-Methods': [
            'GET, POST, PUT, PATCH, DELETE, OPTIONS'
          ],
          // JSON bodies and bearer tokens trigger browser preflight checks.
          'Access-Control-Allow-Headers': ['Content-Type, Authorization']
        }
      })
      return
    }
    callback({})
  })

  // Development uses Vite; packaged apps load their bundled frontend without it.
  if (import.meta.env.QUASAR_DEV) {
    await mainWindow.loadURL(import.meta.env.QUASAR_APP_URL)
  } else {
    await mainWindow.loadFile('index.html')
  }

  if (import.meta.env.QUASAR_DEBUG) {
    // if on DEV or Production with debug enabled
    mainWindow.webContents.openDevTools()
  } else {
    // we're on production; no access to devtools pls
    mainWindow.webContents.on('devtools-opened', () => {
      mainWindow.webContents.closeDevTools()
    })
  }
}

void app.whenReady().then(() => {
  registerQuasarRuntime()
  createWindow()

  app.on('activate', () => {
    // On macOS, clicking the Dock icon reopens the window if it was closed.
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  // Follow macOS's convention of keeping the app running after its window closes.
  if (platform !== 'darwin') {
    app.quit()
  }
})
