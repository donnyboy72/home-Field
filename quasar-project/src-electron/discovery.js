import { Bonjour } from 'bonjour-service'
import { isIPv4 } from 'node:net'

// Advertisements are untrusted hints, never proof of server identity or permission
// to send credentials. Vue requires the user to choose a host before connecting.
export function discoveryResult(service) {
  if (
    service.txt?.app !== 'homefield' ||
    service.txt?.version !== '1' ||
    service.txt?.scheme !== 'http' ||
    !Number.isInteger(service.port) ||
    service.port < 1 ||
    service.port > 65535
  )
    return []
  return [...new Set(service.addresses || [])]
    .filter(
      address =>
        isIPv4(address) &&
        (address.startsWith('10.') ||
          address.startsWith('192.168.') ||
          (address.startsWith('172.') &&
            +address.split('.')[1] >= 16 &&
            +address.split('.')[1] <= 31) ||
          address.startsWith('169.254.'))
    )
    .map(host => ({
      name: String(service.name).slice(0, 100),
      host,
      port: service.port
    }))
}

export function discoverHosts(duration = 4000) {
  return new Promise((resolve, reject) => {
    let bonjour
    let browser
    let timer
    let finished = false
    const hosts = new Map()
    const finish = error => {
      if (finished) return
      finished = true
      clearTimeout(timer)
      browser?.stop()
      bonjour?.destroy()
      if (error)
        reject(
          new Error('Discovery unavailable. Enter the host address manually.')
        )
      else resolve([...hosts.values()].flat().slice(0, 50))
    }
    try {
      bonjour = new Bonjour(undefined, finish)
      browser = bonjour.find({ type: 'homefield', protocol: 'tcp' })
      browser.on('up', service =>
        hosts.set(service.fqdn, discoveryResult(service))
      )
      browser.on('down', service => hosts.delete(service.fqdn))
      // A bounded search closes its multicast socket and lets the user search again.
      timer = setTimeout(() => finish(), duration)
    } catch (error) {
      finish(error)
    }
  })
}
