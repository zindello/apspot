# APSPOT × Beaches On The Air (BOTA) — Integration Proposal

Status: **research / proposal** — no code written yet.
Branch: `feat/add-beaches-on-the-air`

## 1. Summary

Integrating BOTA into APSPOT is technically identical in shape to the POTA and
Tiles integrations — a thin GET→POST wrapper lambda behind `/spot/bota`, routed
through `processmessage`. **The blocker is not on our side: BOTA has no public
API.** Unlike POTA (documented public API) or Tiles (Facundo is standing up a
dedicated endpoint for us), BOTA currently offers no programmatic way to submit
or read spots. Delivery therefore depends on BOTA management providing an
endpoint. This document records the research and defines exactly what we'd build
once/if that exists.

## 2. Research findings (2026-07)

| Question | Finding |
| --- | --- |
| Public spot-submission API? | **None documented.** No `/api`, no developer portal, nothing indexed. |
| Read API for spots? | **None.** Drupal JSON:API root (`/jsonapi`) returns HTTP 404 (module disabled). |
| Platform | **Drupal** (file paths / module naming in markup). |
| Spotting mechanism | Manual, via authenticated web form on the site. Homepage renders a "Latest spots" table (activator, chaser, freq, mode, UTC). |
| Activation reference | **4-character alphanumeric code**, generated per activation at announcement time. |
| Accounts | Individuals only; participants must log activity under their own account. Login at `/user/login`. |
| Auth model | Not documented. |

Sources: beachesontheair.com (home, welcome/getting-started), plus community
write-ups (onallbands, vk5pas, hamradio.my). No source describes an API.

## 3. Options

### Option A — Official endpoint (RECOMMENDED)
Mirror the Tiles playbook: ask BOTA management to expose a small POST endpoint
with a shared secret (`x-api-key`) that APSPOT holds. This is the only path that
is robust, sanctioned, and low-maintenance. Requires an outreach email (draft in
§6) and their willingness to build it.

### Option B — Scrape / unofficial (NOT RECOMMENDED)
Screen-scrape the Drupal site to *read* spots (`SPOTS BOTA`) and/or drive the
web form to *post* spots. Rejected because:
- Fragile: breaks on any Drupal theme/markup change.
- Almost certainly against site terms; posting would require impersonating a
  user's authenticated session — not acceptable.
- Aligns poorly with our "respect upstream sources / no unsanctioned copying"
  stance.

### Option C — Defer
Do nothing until BOTA publishes an API. Zero effort, no capability.

## 4. What we'd build under Option A

Assuming BOTA gives us a POST endpoint that echoes the POTA/Tiles shape, the work
is small and follows the existing pattern exactly:

1. **`lambdas/spot_bota.py`** — new handler. GET query params
   (`callsign`, `ref`, `freq`, `mode`, `comment`) → POST to the BOTA endpoint
   with `x-api-key`. Honour the `APTEST` no-post convention. Return the standard
   `{ "response": "..." }` body. (Direct analogue of `lambdas/spot_tiles.py`.)
2. **`lambdas/processmessage.py`** — add `BOTA` to the accepted spot targets and
   a branch that calls `/spot/bota`; add a `USAGE BOTA` example and list `BOTA`
   in `VALID TARGETS`.
3. **`serverless.yml`** — register a `spotbota` function on `GET /spot/bota`.
4. **`config/<env>.yml`** — add `bota_api_url` and `bota_api_key` (the shared
   secret), consistent with how `tiles_api_*` are parameterised.
5. **APRS container** — no change. `docker/fargate_handler.py` relays
   `! BOTA ...` verbatim to `/processmessage`, so it inherits routing for free
   (same as Tiles).

### Proposed operator UX
```
! BOTA <REF> <FREQ> <MODE> <COMMENT>
e.g.  ! BOTA AB12 14.285 SSB CQ BOTA de portable
```
Note: BOTA's 4-char ref is shorter than POTA/SOTA refs — worth confirming the
`validatemessage` length/format checks accept it.

## 5. Open questions for BOTA management

1. Can you provide a POST spot endpoint? URL + auth (`x-api-key` shared secret
   preferred).
2. Payload shape you want (callsign, ref, frequency units [MHz vs Hz], mode,
   comment)? We can match whatever is easiest for you.
3. Do you validate the activator callsign and reference on your side (so APSPOT
   doesn't have to), as Tiles does?
4. Success/error response contract (e.g. `201 {ok:true}`, `401/422 {reason}`) so
   we can pass a reason back to the operator as an ACK.
5. Rate limits / per-callsign throttling?
6. Is there a test/sandbox endpoint (equivalent to POTA's dev URL) for our
   `APTEST` path?

## 6. Draft outreach email (for Josh to send/adapt)

> Subject: APSPOT integration for Beaches On The Air
>
> Hi <BOTA team>,
>
> I run APSPOT (apspot.radio), a "one format for every program" spotting gateway
> that lets operators spot to POTA, WWFF, SOTA, SIOTA (and soon Tiles On The Air)
> over APRS, SMS and email — useful for offline/portable ops with no internet.
> Users have asked for Beaches On The Air support.
>
> To add BOTA I'd need a small POST endpoint on your side that APSPOT can call
> with a shared secret (x-api-key), roughly mirroring pota.app:
>
>   POST https://<bota-host>/spot
>   x-api-key: <secret-for-APSPOT>
>   { "call_sign": "...", "ref": "AB12", "frequency": 14.285, "mode": "SSB",
>     "comment": "..." }
>
> Ideally you'd validate the activator callsign/reference and rate-limit on your
> end, so I don't carry that logic. I'll match whatever payload shape is easiest
> for you. Happy to test against a sandbox endpoint first.
>
> Is this something you'd consider?  73, Josh

## 7. Effort estimate (Option A, once endpoint exists)

- Handler + routing + serverless + config: ~0.5 day (pattern is established).
- Testing against sandbox + `APTEST` path: ~0.5 day.
- **Total: ~1 day** of work, gated entirely on BOTA providing the endpoint.
