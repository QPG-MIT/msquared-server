## General settings to setup msquared infrastructure
# msquared devices should be on their own LAN: (192.168.1.*) by default
# The HTTP_Entry stuff should listen on the WAN to allow accessing the msquared web interfaces
#   in a more controlled** way
#   ** there currently is not more security than weak IP filtering

## Wavemeter connection (for solstis): Can listen on multiple ports
HW_SERVER_ADDR = ('localhost',36577)
WAVE_LISTEN_ADDR = None  # This needs to match in msquared http config interface. e.g. ('192.168.1.xxx',xxxxx)
# For configuring the channels used, the setup on the solstis itself should index into this list
# NOTE, solstis indexes from 1, and that will be accounted for in msquared_tcp_server
CHANS_USED = { # IP: ((channels,),show_trace)
              None, #for solstis. 'xxx.xxx.xxx.xxx':((chan,),1). 1 to show_trace, 0 to not show_trace. 
              None, #'xxx.xxx.xxx.xxx':((chan,),1) for 2nd solstis
             }


## Configure man-in-the-middle (between solstis and EMM)
## All of these addresses should be on the msquared subnet (LAN)
# EMM will connect to MITM address, and this will then forward to SOLSTIS
MITM_LISTEN_ADDR = None # This needs to match in msquared http config interface ('xxx.xxx.xxx.xxx',xxxxx)
SOLSTIS_ADDR = None # This needs to match the solstis IP ('xxx.xxx.xxx.xxx',xxxxx)

## Configure web interface (msquared listens on http port 80; this is on the LAN)
WAN_ADDR = '0.0.0.0'
WAN_WS_PORT = 8088
# Keys correspond to port on WAN
# Values correspond to full address for ws connection
ROUTES = {
          None, #forwarding address for SolsTiS ('xxx.xxx.xxx.xxx',xxxxx)
          None, #forwarding address for EMM ('xxx.xxx.xxx.xxx',xxxxx)
          None, #forwarding address for pump ('xxx.xxx.xxx.xxx',xxxxx)
          None, #forwarding address for other SolsTiS ('xxx.xxx.xxx.xxx',xxxxx)
          None #forwarding adress for other pump ('xxx.xxx.xxx.xxx',xxxxx)
          }