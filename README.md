APRS Daemon - runs in-house on zindello-server (migrated off AWS Fargate)

Monitors APRS-IS for incoming messages and calls API. Handles sending messages back to APRS-IS.

Built and deployed via `.github/workflows/build-aprs-gateway.yml` on pushes to `fargate/**` —
see `zindello/internal-server`'s `stacks/apspot-aprs/` for the Swarm stack definition.


Email Receive/Response - Lambda

Receives an incoming email. Handles sending messages back via email. Maybe restrict to winlink email addresses?


API:

/spot/wwff?callsign=<callsign>&ref=<ref>&freq=<freq>&mode=<mode>(&comment=<comment>)
/spot/pota?callsign=<callsign>&ref=<ref>&freq=<freq>&mode=<mode>(&comment=<comment>)
/spot/sota?callsign=<callsign>&ref=<ref>&freq=<freq>&mode=<mode>(&comment=<comment>)
/spot/siota?callsign=<callsign>&ref=<ref>&freq=<freq>&mode=<mode>(&comment=<comment>)
/spot/{proxy+}
/spots/pota(?numSpots=<integer>)
/spots/wwff(?numSpots=<integer>)
/spots/sota(?numSpots=<integer>)
/spots/siota(?numSpots=<integer>)
/search/wwff?search=<string>
/search/pota?search=<string>
/search/sota?search=<string>
/search/siota?search=<string>