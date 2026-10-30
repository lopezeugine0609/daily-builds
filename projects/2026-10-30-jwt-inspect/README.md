# jwt-inspect

Offline JWT debugger. Decodes header and payload, reports `iat`/`nbf`/`exp` as ISO time plus relative age, flags expired or not-yet-valid tokens, and verifies HMAC signatures (HS256/HS384/HS512) with a constant-time compare. Also signs test tokens. Node standard library only; the token never leaves your machine.

Safety: `alg: "none"` tokens are flagged and always fail verification. RS/ES/PS algorithms are decoded but not verified.

## Usage

```
node jwt-inspect.js [token|-] [--secret S] [--json] [--now UNIX] [--leeway SEC]
node jwt-inspect.js sign '<payload-json>' --secret S [--alg HS256|HS384|HS512]
```

- Token defaults to stdin when omitted or `-`. A leading `Bearer ` is stripped.
- `--now` overrides the clock (handy for tests); `--leeway` allows clock skew in seconds.
- Exit codes: `0` ok, `1` expired / not-yet-valid / bad signature, `2` malformed token or usage error.

### Examples (real output)

The jwt.io example token, verified with its known secret:

```
$ node jwt-inspect.js eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c --secret your-256-bit-secret --now 1516242622
Header:
{
  "alg": "HS256",
  "typ": "JWT"
}
Payload:
{
  "sub": "1234567890",
  "name": "John Doe",
  "iat": 1516239022
}
Claims:
  iat: 2018-01-18T01:30:22.000Z (1h ago)
  warning: no exp claim, token never expires
Time status: valid
Signature: signature valid
exit 0
```

Sign a token, then inspect it as JSON 10 minutes after expiry:

```
$ X=$(node jwt-inspect.js sign '{"sub":"eugine","exp":1700000000}' --secret k)
$ node jwt-inspect.js $X --secret k --now 1700000600 --json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "eugine",
    "exp": 1700000000
  },
  "time": "expired",
  "signature": true,
  "notes": [
    "exp: 2023-11-14T22:13:20.000Z (10m ago)"
  ]
}
exit 1
```

Malformed input:

```
$ node jwt-inspect.js not.a-token
malformed token: expected 3 dot-separated parts, got 2
exit 2
```

## Tests

```
node --test
```

12 tests: jwt.io vector decode/verify, sign/verify roundtrip for all HMAC algs, tampered payload, `alg: none` refusal, malformed-input errors, time-claim logic with leeway, duration formatting, CLI exit codes, stdin + JSON mode.
