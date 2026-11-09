import { test } from 'node:test'
import assert from 'node:assert/strict'
import { discoveryResult } from '../discovery.js'

const service = {
  name: 'Classroom HomeField',
  port: 50000,
  txt: { app: 'homefield', version: '1', scheme: 'http' },
  addresses: ['192.168.1.5', '10.0.0.4']
}

test('returns distinct LAN addresses and the advertised port', () => {
  const results = discoveryResult({
    ...service,
    addresses: [...service.addresses, '192.168.1.5']
  })
  assert.deepEqual(
    results.map(host => host.host),
    service.addresses
  )
  assert.equal(results[0].port, 50000)
})

test('ignores public, loopback, malformed and IPv6 addresses', () => {
  assert.deepEqual(
    discoveryResult({
      ...service,
      addresses: ['8.8.8.8', '127.0.0.1', '192.168.1.999', '172.32.0.1', '::1']
    }),
    []
  )
})

test('rejects unsupported protocols, versions, and invalid ports', () => {
  for (const port of [0, 65536, '50000']) {
    assert.deepEqual(discoveryResult({ ...service, port }), [])
  }
  assert.deepEqual(
    discoveryResult({ ...service, txt: { ...service.txt, scheme: 'https' } }),
    []
  )
  assert.deepEqual(
    discoveryResult({ ...service, txt: { ...service.txt, version: '2' } }),
    []
  )
  assert.deepEqual(discoveryResult({ ...service, txt: null }), [])
})
