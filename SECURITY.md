# Security Model and Authentication Requirements

## Status

This repository currently defines a collaboration protocol and shared-file conventions. The documented message schema is **not an authentication mechanism**. A `sender` value, a handshake message, a timestamp, or an append-only log does not prove who authored a message.

This document specifies the minimum security requirements for any runtime or integration that reads from or writes to this workspace. It does not claim those controls are implemented by this repository.

## Trust boundaries

Treat each of the following as a separate trust boundary:

1. **Contributor identity** — which human, agent runtime, service, or automation is making a request.
2. **Transport and repository access** — whether the caller is authenticated to the API, host, Git provider, or filesystem.
3. **Message integrity** — whether the message contents were altered after they were authored.
4. **Authorization** — whether that authenticated identity may read or modify the requested resource.
5. **Audit history** — whether changes can be detected, attributed, and investigated.

Passing one boundary must not imply passing the others. In particular, GitHub authentication authenticates a GitHub account to GitHub; it does not by itself prove that a JSONL message's claimed `sender` is truthful.

## Minimum requirements before enabling automated writes

- Require authentication at the write boundary. Do not accept unauthenticated network writes to shared files.
- Map verified credentials to a stable internal principal. Never derive authorization from a caller-supplied `sender`, `agent_id`, or display name.
- Authorize each operation against an explicit policy: resource, action, principal, and scope. Default to deny.
- Keep credentials out of source files, communication logs, task state, URLs, and error messages. Use a secret manager or the hosting platform's protected secret store.
- Use TLS for network transport. Do not transmit bearer tokens in query strings.
- If bearer tokens are used, validate signature or introspection, issuer, audience, expiry, and relevant scopes. Use short-lived access tokens; rotate/revoke credentials and tokens where supported. Do not invent a refresh-token flow unless the system actually implements one.
- If messages need independently verifiable authorship across different runtimes, use authenticated transport and/or signed messages. A signature must cover a canonical representation of the relevant fields, including sender, target, type, timestamp, and content. Verify signatures against a trusted key-to-principal registry. Define key rotation and revocation.
- Treat timestamps as untrusted input until validated. Check format, clock skew, message size, allowed message types, and required fields.
- Enforce append-only behavior at the storage layer, not merely by convention. Restrict who can append, and use protected audit storage or signed/hash-chained records if tamper evidence is required.
- Protect private agent directories using actual repository or storage permissions. A statement in Markdown is not an access-control boundary.
- Avoid logging secrets, authorization headers, raw session cookies, or bearer tokens. Log the principal, action, resource, result, and correlation ID instead.
- Test unauthorized, expired-token, wrong-audience, insufficient-scope, forged-sender, replay, and concurrent-write cases.

## Recommended request flow

1. Receive the request over an authenticated, encrypted transport.
2. Authenticate the credential or token; reject missing, invalid, expired, revoked, or incorrectly scoped credentials.
3. Resolve the verified credential to a stable principal.
4. Validate the request schema and enforce size/type/time limits.
5. Authorize the principal for the exact requested action and resource.
6. Apply the operation using a storage boundary that enforces permissions and concurrency controls.
7. Record a security audit event without storing credentials or tokens.
8. Return the minimum response needed; do not reveal whether a secret or account exists unless required.

A message-level `handshake` may be useful for coordination after authentication, but it must not substitute for steps 2–5.

## Current known limitations

The currently documented protocol defines `timestamp`, `sender`, `target`, `type`, and `content`. It does not define credential issuance, token validation, signature verification, key distribution, authorization policy, or revocation. No runtime implementation of these controls has been established from the files in this repository.

Do not describe the workspace as authenticated or secure until the relevant enforcement code and configuration exist and have been tested.
