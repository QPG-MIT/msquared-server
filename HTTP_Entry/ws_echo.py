from SimpleWebSocketServer.SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
from websocket import create_connection
import threading, logging, sys, json, os
logger = logging.getLogger()

# NOTE: msquared will try to bind the ws to 8088 by default, so we will listen there.
# The http_echo.py fixes a typo in their js, such that the origin address of the ws request was incorrect.

logLevel = logging.INFO

# Load settings (adding one directory up to the path)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(BASE_DIR,'..')))
import settings
WAN_ADDR = settings.WAN_ADDR
WAN_PORT = settings.WAN_WS_PORT
routes = settings.ROUTES

try: os.system("title "+'ws_echo (msquared)')
except: pass

CLIENTS = {}

def update_clients(client,opening=True):
    global CLIENTS
    # client.address is binding address
    # client.port is origin port
    if opening: # Opening
        if client.address[0] not in CLIENTS:
            CLIENTS[client.address[0]] = {port:0 for port in routes}
        CLIENTS[client.address[0]][client.port] += 1   
    else: # Closing
        CLIENTS[client.address[0]][client.port] -= 1
    logger.info('Update:\n%s'%json.dumps(CLIENTS,sort_keys=True,indent=2))

class Relay(WebSocket):
    def __init__(self,*args,**kwargs):
        super(Relay,self).__init__(*args,**kwargs)
        self.outgoing = None
        self.thread = None
        self.stop = False
        self.port = None

    def handle_outgoing(self):
        # Run as separate thread
        try:
            while not self.stop:
                msg = self.outgoing.recv()
                logger.debug(msg)
                self.sendMessage(msg)
        except:
            logger.exception('Error in outgoing recv loop')
        finally:
            logger.info('closing socket (handle outgoing)')
            self.outgoing.close()

    def handleMessage(self):
        logger.debug(self.data)
        self.outgoing.send(self.data)

    def handleConnected(self):
        logger.info('%s:%i connected'%self.address)
        header = self.headerbuffer.decode('utf-8')
        GET = ''
        for line in header.split('\n'):
            if not GET: # Line 1
                GET = line.split(' ')[1] # Format: GET URL HTTP/version
            line = line.strip() # Clean up windows line endings
            line = line.split(': ')
            [key,args] = [line[0],': '.join(line[1:])]
            if key == 'Origin':
                origin_port = int(args.split(':')[-1])
                dst = routes[origin_port]
                break
        self.port = origin_port
        URL = 'ws://%s:%i%s'%(dst[0],dst[1],GET)
        self.outgoing = create_connection(URL)
        logger.info('outgoing connected: %s'%URL)
        # Spawn thread to handle other connections
        self.thread = threading.Thread(target=self.handle_outgoing)
        self.thread.start()
        update_clients(self,True)

    def handleClose(self):
        self.stop = True
        self.thread.join(5)
        update_clients(self,False)
        logger.info('%s:%i closed'%self.address)


if __name__=='__main__':
    logger.setLevel(logLevel)
    formatter = logging.Formatter('[%(asctime)s] %(levelname)-7.7s %(message)s')
    str_handler = logging.StreamHandler(sys.stdout)
    str_handler.setFormatter(formatter)
    str_handler.setLevel(logLevel)
    logger.addHandler(str_handler)

    logger.info('starting server...')
    server = SimpleWebSocketServer(WAN_ADDR, WAN_PORT, Relay)
    logger.info('running server...')
    server.serveforever()
