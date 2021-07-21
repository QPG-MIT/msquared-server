from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import requests, sys, logging, threading, time, os
from base64 import b64decode
logger = logging.getLogger()

logLevel = logging.INFO

# Load settings (adding one directory up to the path)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(BASE_DIR,'..')))
import settings
WAN_ADDR = settings.WAN_ADDR
routes = settings.ROUTES

try: os.system("title "+'http_echo (msquared)')
except: pass

# HTTPRequestHandler class
class RequestHandler(BaseHTTPRequestHandler):

    # GET
    def do_GET(self):
        if 'Authorization' in self.headers:
            pw = b64decode(self.headers['Authorization'].split(' ')[1]).decode('utf8')
            logger.info('%s->%s: GET %s (%s)',self.client_address[0],routes[self.server.server_port][0],self.path,pw)
        else:
            logger.info('%s->%s: GET %s',self.client_address[0],routes[self.server.server_port][0],self.path)

        if self.client_address[0][0:2] != 'xx': # Extremely poor filtering. replace xx with first nums of your IP, or remove this altogether
            #make it so only certain classes of IPs can access 
            self.send_response(403)
            self.send_header('Content-type','text/html')
            self.end_headers()
            self.wfile.write('Rejected by IP'.encode('utf-8'))
            logger.warning('%s rejected',self.client_address[0])
            return

        r = requests.get('http://%s%s'%(routes[self.server.server_port][0],self.path),headers=self.headers)
        # Send response status code
        self.send_response(r.status_code)
        # Send headers
        [self.send_header(key,r.headers[key]) for key in r.headers if key.lower() != 'transfer-encoding']
        self.end_headers()
        # Write content as utf-8 data
        content = r.content
        if os.path.splitext(self.path)[1] == '.js': #  Fix their typo
            logger.debug('host -> hostname')
            content = content.replace(b'window.location.host',b'window.location.hostname')
        self.wfile.write(content)
        logger.debug('Finished')

    def log_message(self, format, *args):
        return

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
 
class threads:
    def __init__(self):
        self.threads = {}

    def stop_all(self):
        for port in self.threads:
            logger.info('Shutting down port %i'%port)
            self.threads[port][0].shutdown()
            #self.threads[port][1].join(1)

    def poll(self):
        for port in self.threads:
            if not self.threads[port][1].isAlive():
                logger.info('httpd %i died, re-running'%port)
                self.run(port)

    def run(self,port):    
        # Server settings
        server_address = (WAN_ADDR, port)
        httpd = ThreadedHTTPServer(server_address, RequestHandler)
        t = threading.Thread(target=httpd.serve_forever)
        self.threads[port] = (httpd,t)
        t.start()
        logger.info('running server (%i)...'%port)
 
if __name__=='__main__':
    logger.setLevel(logLevel)
    formatter = logging.Formatter('[%(asctime)s] %(levelname)-7.7s %(message)s')
    str_handler = logging.StreamHandler(sys.stdout)
    str_handler.setFormatter(formatter)
    str_handler.setLevel(logLevel)
    logger.addHandler(str_handler)
    
    thread_tracker = threads()
    threads = []
    for port in routes:
        thread_tracker.run(port)
    while True: # Serve forever until ctrl-c. Long live the msquared server!
        try:
            time.sleep(1)
            thread_tracker.poll()
        except KeyboardInterrupt:
            logger.info('Stopping all httpd')
            thread_tracker.stop_all()
            break
