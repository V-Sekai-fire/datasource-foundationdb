# flowquic, rung A: picoquic driven by Flow's Net2

`flowquic/` (option `FLOWQUIC`, default OFF) runs a picoquic server and client in one process on one Net2 loop. Flow owns both UDP sockets (`IUDPSocket::receiveFrom` / `sendTo`) and the clock; picoquic is a state machine fed by `picoquic_incoming_packet` and drained by `picoquic_prepare_next_packet_ex`. No picoquic packet loop, no thread, no lock. TLS is OpenSSL (flow already links it); RFD66606-2261 wants mbedTLS, so this is a recorded deviation. picoquic is pinned at a6f85e8a, unchanged.

Run: aarch64 Linux container, clang, loopback, `FDB_USE_CSHARP_TOOLS=OFF`. Recipes: `flowquic/build-in-container.sh`, `flowquic/run-in-container.sh`.

| Run | Runs | Result |
| --- | --- | --- |
| positive: client trusts `test-ca.crt`, 192 datagrams of 1200 bytes at 64 Hz | 3 | 3 of 3 passed: 192 of 192 datagrams echoed, handshake ok |
| control: client trusts `badcert.pem` | 2 | 2 of 2 passed: handshake refused, TLS alert 48 (unknown_ca), 0 datagrams received |

The control is not vacuous: the client uses strict verification, and the same binary passes the positive run.

## Bug found in the fork's Net2

Before the fix, the same positive run passed but the log showed 2 of 4 handshake packets per side dropped. `ReadPromise`'s move constructor did not move `endpoint`, so `UDPSocket::receiveFrom` wrote the sender into freed memory; the sender came back as a garbage IPv6 address and `toV4()` threw `bad_variant_access`, which ended the actor as `unknown_error`. QUIC retransmission hid it. After moving `endpoint` in the move constructor: 0 exceptions, every socket-level packet reaches picoquic (client 394 out, server 394 in).

## Not shown

Windows, x86_64, mbedTLS, a path MTU other than loopback, h3zero / WebTransport (rung B), and the entity tick. The scenario's diagnostic counters are still in the source.

## Rung B: HTTP/3 and WebTransport on the same loop

Same driver; `BUILD_HTTP` on, `picohttp-core` linked, ALPN `h3`. The server serves a WebTransport CONNECT at `/echo` and echoes every session datagram; the client opens the session and counts the echoes. Run with the trailing `wt` argument.

| Run | Result |
| --- | --- |
| positive, 192 datagrams of 1200 bytes at 64 Hz | PASS: 192 of 192 echoed through the session |
| control, client trusts `badcert.pem` | PASS: handshake refused, TLS alert 48, 0 datagrams |
| badpath, CONNECT to `/nope` | PASS: refused once, session not opened, 0 datagrams |
| rung A positive again (no `wt`) | PASS: 192 of 192 |

Each Rung B row ran once. The badpath control exercises the HTTP/3 layer, because TLS and QUIC succeed there. Same limits as rung A: aarch64 Linux container, loopback, OpenSSL, no Windows. The diagnostic counters and `FLOWQUIC_DEBUG` are still in the source.
