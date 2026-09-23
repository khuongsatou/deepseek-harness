/**
 * Browser-safe, zero-dependency loopback and trusted-authority classification
 * shared by the `/api` Host fence and the package's `ctx.connection` state.
 * Consumed by Host and client plugins through Cordis.
 */

/**
 * Whether a normalized URL hostname names the local loopback authority.
 * @param hostname - WHATWG URL hostname (IPv6 literals retain brackets).
 * @returns true for localhost, IPv6 loopback, or any IPv4 address in 127/8.
 */
export function isLoopbackHostname(hostname: string): boolean {
  if (hostname === 'localhost' || hostname === '[::1]') return true
  const parts = hostname.split('.')
  return parts.length === 4
    && parts[0] === '127'
    && parts.every(part => /^\d{1,3}$/.test(part) && Number(part) <= 255)
}

/**
 * Normalized URL of a Host-header authority (hostname lowercased, default port stripped, IPv6 bracketed), or undefined when unparsable.
 * @param authority - bare authority string to parse.
 * @returns parsed URL or undefined if unparsable.
 */
export function parseAuthority(authority: string): URL | undefined {
  try {
    // http: is a WHATWG "special scheme": parsing yields a non-empty hostname or throws.
    return new URL(`http://${authority}`)
  } catch {
    return undefined
  }
}

/**
 * Canonical form of a parsed authority: `hostname` when no port was written,
 * else `hostname:port`. The port is judged from URL parses under both special
 * schemes (their default ports differ, so `:80` and `:443` still count as
 * explicit), never from the raw string, where WHATWG trimming would misread
 * shapes like `host:port ` as port-less.
 * @param entry - the configured value, verbatim.
 * @param entryUrl - parsed URL of the entry.
 * @returns canonical authority string.
 */
export function canonicalAuthority(entry: string, entryUrl: URL): string {
  // An authority that parsed under http cannot fail under https.
  const port = entryUrl.port !== '' ? entryUrl.port : new URL(`https://${entry}`).port
  return port === '' ? entryUrl.hostname : `${entryUrl.hostname}:${port}`
}

/**
 * Whether the authority matches a `trustedHosts` entry. An entry with an
 * explicit port matches that exact authority; a port-less entry matches the
 * hostname on any port (the shape the CLI derives for IP-literal LAN serving,
 * where the bound port may be OS-assigned). Both sides compare through WHATWG
 * normalization, so case and a redundant `:80` never decide trust.
 * @param hostAuthority - URL or string authority to test.
 * @param trustedHosts - non-loopback authorities to match against.
 * @returns true if hostAuthority matches any pattern in trustedHosts.
 */
export function isTrustedAuthority(hostAuthority: URL | string, trustedHosts: readonly string[]): boolean {
  const hostUrl = typeof hostAuthority === 'string' ? parseAuthority(hostAuthority) : hostAuthority
  if (hostUrl === undefined) return false
  return trustedHosts.some((entry) => {
    const entryUrl = parseAuthority(entry)
    if (entryUrl === undefined) return false
    return canonicalAuthority(entry, entryUrl) === entryUrl.hostname
      ? entryUrl.hostname === hostUrl.hostname
      : entryUrl.host === hostUrl.host
  })
}
