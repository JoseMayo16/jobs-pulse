"""Job board connectors.

Every board module exposes the same small interface, so adding a source means
writing one file and registering it in BOARDS:

    NAME   short id stored with each listing
    LABEL  display name, used for attribution on the dashboard
    HOME   link back to the board (required by their API terms)
    fetch(client) -> raw JSON
    parse(raw) -> list[Listing]

`fetch` does the network call and `parse` is pure, so tests feed recorded
fixtures straight into `parse`.
"""

from . import arbeitnow, remoteok, remotive

BOARDS = (remotive, remoteok, arbeitnow)
