# Security Model and Authentication Requirements

## Status

This repository defines collaboration protocols and shared-file conventions. The documented message schema is **not an authentication mechanism**. A `sender` value, handshake message, timestamp, or append-only log does not prove who authored a message.

This document specifies minimum requirements for any runtime or integration that reads from or writes to this workspace. It does not claim that repository files alone implement those controls.

## Trust boundaries

Treat each as a separate trust boundary:

1. **Contributor identity** — which human, agent runtime, service, or automation is making a request.
2. **Transport and repository access** — whether the caller is authenticated to the API, host, Git provider, or filesystem.
3. **Message integrity** — whether contents were altered after authorship.
4. **Authorization** — whether that authenticated identity may read or modify the requested resource.
5. **Audit history** — whether changes can be detected, attributed, and investigated.

Passing one boundary must not imply passing the others. GitHub authentication authenticates a GitHub principal to GitHub; it does not prove that a JSONL message's claimed `sender` is truthful.

## Minimum requirements before enabling automated writes

- Require authentication at the write boundary. Do not accept unauthenticated network writes to shared files.
- Map verified credentials to a stable internal principal. Never derive authorization from a caller-supplied `sender`, `agent_id`, or display name.
- Authorize each operation against an explicit policy: resource, action, principal, and scope. Default to deny.
- Keep credentials out of source files, communication logs, task state, URLs, and error messages. Use a secret manager or protected platform secret store.
- Use TLS for network transport. Do not transmit bearer tokens in query strings.
- Validate token signature/introspection, issuer, audience, expiry, and scopes where applicable. Use short-lived credentials and supported rotation/revocation.
- If messages need independently verifiable authorship across runtimes, use authenticated transport and/or signed messages with a trusted key registry, rotation, and revocation.
- Treat timestamps as untrusted input until validated. Check format, clock skew, message size, allowed types, and required fields.
- Enforce append-only behaviour at the storage layer when tamper evidence is required. Restrict who can append and use protected audit storage or signed/hash-chained records where appropriate.
- Protect private agent directories using actual repository/storage permissions. A Markdown statement is not an access-control boundary.
- Avoid logging secrets, authorization headers, raw session cookies, or bearer tokens. Log principal, action, resource, result, and correlation ID instead.
- Test unauthorized, expired-token, wrong-audience, insufficient-scope, forged-sender, replay, and concurrent-write cases.

## Recommended request flow

1. Receive the request over authenticated, encrypted transport.
2. Authenticate the credential or token; reject missing, invalid, expired, revoked, or incorrectly scoped credentials.
3. Resolve the verified credential to a stable principal.
4. Validate the request schema and enforce size/type/time limits.
5. Authorize the principal for the exact requested action and resource.
6. Apply the operation using a storage boundary with permissions and concurrency controls.
7. Record a security audit event without credentials or tokens.
8. Return the minimum response needed.

A message-level `handshake` may be useful for coordination after authentication, but it must not substitute for steps 2–5.

## Repository-level safety checks

`python scripts/security_audit.py` performs static checks for common repository hazards such as secret-like assignments, bearer-token material, private-key blocks, unsafe sender-based authorization patterns, and accidental credentials in coordination records. It is a hygiene check, not proof of security.

CI should run it on changes affecting the coordination substrate. Runtime authentication and authorization remain deployment responsibilities until an actual enforcement service is committed and tested.

## Current known limitations

Central currently defines credential and authorization requirements but does not implement credential issuance, token validation, signed-message verification, key distribution, revocation, or runtime identity binding. The dashboard is a read-only browser view and must not be treated as an authenticated write boundary.

Do not describe the workspace as authenticated or secure until the relevant enforcement code and configuration exist and have been tested.
