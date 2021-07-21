https://github.mit.edu/mpwalsh/msquared_server

# msquared_server (python > 3)
Reverse engineering of msquared TCP Server

## The main files:
### msquared_tcp_server.py

This is responsible to interface with the wavemeter.
The exe distributed by msquared is overly aggressive with the wavemeter and prevents us from using the switching capability.
This drop-in replacement server behaves with the switch and won't overwrite every setting on other channels (namely PID settings).
It is built to interface with the hwserver and expects the hwserver to have the "wavemeter" module loaded.

The SOLSTIS should be set to connect to settings.WAVE_LISTEN_ADDR for its wavemeter network config (via the web interface).

### man_in_the_middle.py

This server allows switching between hwserver and EMM control of the SOLSTIS. When disabled, the hwserver can talk directly to the SOLSTIS. When enabled, the EMM is patched in preventing hwserver connections to the SOLSTIS.

The EMM should be set to connect to settings.MITM_LISTEN_ADDR (the LAN address this program listens on). The SOLSTIS should be set to allow third-party connections from this same address.

### HTTP_Entry

The collection of these files allows forwarding web interface to the msquared products on the LAN. There are a few bugs in the msquared original code, so this also takes care of patching those issues in the html.

**This is not yet SSL secured!** It should be considered equally as vulnerable as the native msquared web interface right now (which is not secured by the password they request).

#### http_echo.py

The server is setup to listen on ports specified as the keys in settings.ROUTES on the WAN interface.
A typo in their js files for initiating a websocket (when port forwarding) is fixed which is necessary for this scheme to work.
It is less efficient than serving our own version of their code, but more flexible to msquared updates.
In fact, an update that changes the port from 8088 for their websockets will break this (see ws_echo.py)

#### ws_echo.py

This server listens on port 8088 (hard-coded in msquared's js files).
It uses the origin meta data from the connection to differentiate between devices (specified in settings.ROUTES).
It then forwards the connection to the msquared device and leaves it open until you close the webpage (e.g. the client closes the connection).
