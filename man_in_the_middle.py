import errno # To catch specific socket errors
import socket, sys, os, traceback, json
import SetupLogging.SetupLogging as log
import logging, select
# Load settings
import settings

# Uses sys.stderr to signal client connected (after first exchange)
# Useful if subprocessing to PIPE

filename = os.path.splitext(os.path.abspath(__file__))[0]
logger = log.setup_logger(filename+'.log',logging.INFO,logging.INFO)  # file, stream

class ClientDisconnected(IOError):
    pass

SOLSTIS_ADDR = settings.SOLSTIS_ADDR
# IGNORE_OPS is simply for logging purposes
IGNORE_OPS = ['get_status','poll_wave_m','etalon_lock_status','ecd_lock_status','get_alignment_status','read_all_adc']
temp = [] # Include the replies too
for op in IGNORE_OPS:
    temp.append(op+'_reply')
IGNORE_OPS += temp
logger.critical('Assuming SolsTiS on %s:%i'%SOLSTIS_ADDR)

# Setup Server for msquared stuff
SERVER_IP = settings.MITM_LISTEN_ADDR[0]
SERVER_PORT = settings.MITM_LISTEN_ADDR[1]
SERVER = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
SERVER.settimeout(1)
SERVER.bind((SERVER_IP,SERVER_PORT))
SERVER.listen(1)
logger.critical('Server listening on %s:%i'%(SERVER_IP,SERVER_PORT))

def recvjson(connection,recv_buffer=4096):
    buffer = b''
    while True:
        data = connection.recv(recv_buffer)
        if not data: raise ClientDisconnected('Client disconnected.')
        buffer += data
        logger.debug(buffer)
        try:
            return json.loads(buffer)
        except ValueError:
            pass

# Server methods
def get_client():
    while True:
        try:
            return SERVER.accept()
        except socket.timeout:
            pass

def exchange(frm,to,log_prepend):
    try:
        msg = recvjson(frm)
        if msg['message']['op'] == 'parse_fail':
            raise Exception('protocol_error: %i'%msg['message']['parameters']['protocol_error'][0])
        if 'ip_address' in json.dumps(msg):
            logger.debug('modified ip')
            msg['message']['parameters']['ip_address'] = SERVER_IP
        msgStr = json.dumps(msg)
        to.sendall(bytes(msgStr,'utf-8'))
        if msg['message']['op'] not in IGNORE_OPS:
            logger.debug(log_prepend+msgStr)
    except socket.timeout:
        pass

def handle_client(EMM,ip):
    SOLSTIS = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    SOLSTIS.settimeout(1)
    SOLSTIS.connect(SOLSTIS_ADDR)
    first = [0, 0] # EMM, SOLSTIS each can be 0,1,2
    try:
        while True:  # Each loop, look for messages from both sides
            ready = select.select([EMM,SOLSTIS],[],[],1)[0]
            for dev in ready:
                if dev == EMM:
                    logger.debug('EMM ready')
                    exchange(EMM,SOLSTIS,'>')
                    if first[0]==0: first[0] = 1
                else:
                    logger.debug('SOLSTIS ready')
                    exchange(SOLSTIS,EMM,'<')
                    if first[1]==0: first[1] = 1

                if first[0]==1 and first[1]==1:
                    print(ip[0],file=sys.stderr) # Signal all good after both have spoken
                    sys.stderr.flush()
                    first = [2,2] # Done

    finally:
        SOLSTIS.close()

if __name__ == '__main__':
    try:
        os.system("title man_in_the_middle (listening: %s:%i)"%(SERVER_IP,SERVER_PORT))
        while True:  # main loop
            logger.debug('Waiting for EMM.')
            EMM,ip = get_client()
            os.system("title man_in_the_middle (connected: %s)"%ip[0])
            EMM.settimeout(1)
            logger.info('New EMM: %s'%ip[0])
            try:
                handle_client(EMM,ip)
            except (socket.timeout,ClientDisconnected,ConnectionResetError):
                logger.exception('Client Disconnected')
            except KeyboardInterrupt:
                break
            except:
                logger.critical('Error in main EMM loop')
            finally:
                EMM.close()
    finally:
        SERVER.close()
        logger.critical('Stopping server.')
