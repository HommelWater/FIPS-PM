#!/usr/bin/env python3
import http.server, socketserver, socket, dns.resolver

NPUB = "npub1h7p6lg5xtc6c7kq8aumhmu8xcvq6vratvs59dv0e276eas2rrt7sf8u4vv"
PORT = 8080

# Resolve for display only
r = dns.resolver.Resolver()
r.nameservers, r.port = ["127.0.0.1"], 5354
IPV6 = str(r.resolve(f"{NPUB}.fips", "AAAA")[0])

print(f"Serving on:")
print(f"  http://{NPUB}.fips:{PORT}/  (FIPS)")
print(f"  http://[{IPV6}]:{PORT}/  (IPv6)")
print(f"  http://localhost:{PORT}/  (local)\n")

# Bind to ALL interfaces - FIPS routes fd00:: traffic here
socketserver.TCPServer.address_family = socket.AF_INET6
with socketserver.TCPServer(("::", PORT), http.server.SimpleHTTPRequestHandler) as s:
    s.serve_forever()