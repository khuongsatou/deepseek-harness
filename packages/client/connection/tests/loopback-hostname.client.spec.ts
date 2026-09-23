/** Shared loopback-hostname semantics for the Host fence and browser UI. */

import { describe, expect, it } from 'vitest'
import {
  canonicalAuthority,
  isLoopbackHostname,
  isTrustedAuthority,
  parseAuthority,
} from '../src/loopback-hostname.ts'

describe('isLoopbackHostname', () => {
  it('accepts localhost, IPv6 loopback, and the whole IPv4 127/8 block', () => {
    for (const hostname of ['localhost', '[::1]', '127.0.0.1', '127.8.9.10', '127.255.255.255']) {
      expect(isLoopbackHostname(hostname)).toBe(true)
    }
  })

  it('refuses malformed and non-loopback hostnames', () => {
    for (const hostname of ['remote.localhost', '::1', '128.0.0.1', '127.0.0', '127.0.0.256', '127.0.0.-1']) {
      expect(isLoopbackHostname(hostname)).toBe(false)
    }
  })
})

describe('isTrustedAuthority', () => {
  it('matches port-less trusted entries on any port', () => {
    const trusted = ['dp.1nutnhan.com', 'harness.example']
    expect(isTrustedAuthority('dp.1nutnhan.com', trusted)).toBe(true)
    expect(isTrustedAuthority('dp.1nutnhan.com:3080', trusted)).toBe(true)
    expect(isTrustedAuthority('DP.1nutnhan.com', trusted)).toBe(true)
    expect(isTrustedAuthority('harness.example:443', trusted)).toBe(true)
    expect(isTrustedAuthority('other.example', trusted)).toBe(false)
  })

  it('matches explicit-port trusted entries only on the matching port', () => {
    const trusted = ['dp.1nutnhan.com:3080']
    expect(isTrustedAuthority('dp.1nutnhan.com:3080', trusted)).toBe(true)
    expect(isTrustedAuthority('dp.1nutnhan.com', trusted)).toBe(false)
    expect(isTrustedAuthority('dp.1nutnhan.com:8080', trusted)).toBe(false)
  })

  it('handles URL instances and unparsable inputs gracefully', () => {
    const trusted = ['dp.1nutnhan.com']
    const url = parseAuthority('dp.1nutnhan.com')!
    expect(isTrustedAuthority(url, trusted)).toBe(true)
    expect(isTrustedAuthority('not an authority:bad:port:99999', trusted)).toBe(false)
    expect(canonicalAuthority('dp.1nutnhan.com', url)).toBe('dp.1nutnhan.com')
  })
})
