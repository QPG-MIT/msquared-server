import os, sys, socket, logging, traceback, json, re, time, threading
import errno # To catch specific socket errors
import SetupLogging.SetupLogging as log
if sys.version_info[0] > 2:
    import urllib.parse as urllib
else:
    import urllib
# Load settings
import settings

class ClientDisconnected(IOError):
    pass

# Setup logging
PATH = os.path.dirname(os.path.realpath(__file__))
filename = os.path.splitext(os.path.basename(__file__))[0]
logFile = os.path.join(PATH,filename+'.log')
logger = log.setup_logger(logFile,logging.INFO,logging.INFO)  # file, stream

USER_EXIT = False # Used between threads
# Setup Server for msquared stuff (just on the 192.* address)
SERVER_IP = settings.WAVE_LISTEN_ADDR[0]
SERVER_PORT = settings.WAVE_LISTEN_ADDR[1]
SERVER = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
SERVER.settimeout(1)
SERVER.bind((SERVER_IP,SERVER_PORT))
SERVER.listen(1)
TRANSMISSION_ID = {} # Key IP, val transmission ID
logger.critical('Server listening on %s:%i'%(SERVER_IP,SERVER_PORT))

# Setup Client for hwserver
HW_IP = settings.HW_SERVER_ADDR[0]
HW_PORT = settings.HW_SERVER_ADDR[1]

try:
    os.system("title "+filename+" (%s: %i)"%(SERVER_IP,SERVER_PORT))
except:
    pass

class ForeignMessage(Exception):
    pass

# Translators
def from_msquared(msquared_msg,ip):
    task = msquared_msg['message']['transmission']['task1']
    if task['name'] == 'start-link':
        msg = []
    elif task['name'] == 'configure-wlm':
        ind = task['parameters']['channel'][0]-1 # Index into settings.CHANS_USED
        msg = []
        chans_avail,show = settings.CHANS_USED[ip]
        for i in range(len(chans_avail)):
            chan = chans_avail[i]
            if i == ind:
                msg.append(('SetSwitcherSignalStates',chan,1,show))  # Activates channel if not already
            else:
                msg.append(('SetSwitcherSignalStates',chan,0,0))  # Deactivate other ones
    elif task['name'] == 'check-wlm-server':
        msg = []
    elif task['name'] == 'set-measurement-op':
        msg = []
    elif task['name'] == 'wlm-server-app':
        msg = []
    elif task['name'] == 'get-wavelength':
        ind = task['parameters']['channel'][0]-1 # Index into settings.CHANS_USED
        chan = settings.CHANS_USED[ip][0][ind]  # The 0 index is to select the channel tuple in the list
        msg = [('GetWavelengthNum',chan,0)]
    elif task['name'] == 'set-switch':  # "Handle" this in configure-wlm
        msg = []
    elif task['name'] == 'set-exposure':
        msg = []
    else:
        raise ForeignMessage('Unseen request from msquared: %s'%json.dumps(msquared_msg))
    return msg

def to_msquared(msquared_req, msg, ip):
    global TRANSMISSION_ID
    task_req = msquared_req['message']['transmission']['task1']
    task_rep = {'name':task_req['name']+'-reply',
                'id':task_req['id']}  # Echo request id
    parameters = {}
    # task-specific parameters
    if task_req['name'] == 'start-link':
        parameters['status'] = 'ok'
        parameters['ip-address'] = SERVER_IP
    elif task_req['name'] == 'configure-wlm':
        for param in task_req['parameters']:
            parameters[param] = 'ok'
        parameters['pid-t'] = 'failed'
        parameters['pid-dt'] = 'failed'
        parameters['sensitivity-factor'] = 'failed'
        parameters['channel'] = task_req['parameters']['channel']
    elif task_req['name'] == 'check-wlm-server':
        parameters['status'] = 'active'
    elif task_req['name'] == 'set-measurement-op':
        parameters['status'] = 'ok'
    elif task_req['name'] == 'wlm-server-app':
        parameters['status'] = 'ok'
    elif task_req['name'] == 'get-wavelength':
        status = 'ok'
        wavelength = [0]
        if msg == 0:
            status = 'no-value'
        elif msg == -1:
            status = 'low-signal'
        elif msg == -2:
            status = 'high-signal'
        else:
            wavelength = [msg]
        parameters['status'] = status
        parameters['wavelength'] = wavelength
        parameters['calibration'] = 'inactive'
        parameters['mode'] = 'fixed'  # msquared doesnt need to know
        parameters['configuration'] = 'ok'
        parameters['channel'] = task_req['parameters']['channel']
    elif task_req['name'] == 'set-switch':  # "Handle" this in configure-wlm
        parameters['status'] = 'ok'
    elif task_req['name'] == 'set-exposure':
        parameters['status'] = 'ok'
    # Finish building reply
    if parameters:
        task_rep['parameters'] = parameters
    response = {'message':{'transmission-id':[TRANSMISSION_ID[ip]],
                           'task-count':[1],
                           'transmission':{'task1':task_rep}
                           }
                }
    TRANSMISSION_ID[ip] += 1
    return json.dumps(response)

# Read/Write methods
def recvline(connection,delim=b'\n',recv_buffer=4096):
    # Wrapper to recv until newline
    buffer = b''
    while True:
        data = connection.recv(recv_buffer)
        if not data: raise ClientDisconnected('Client disconnected while receiving.')
        buffer += data
        if data[-1:] == delim:
            return buffer[0:-len(delim)].decode('utf-8')   # Remove delim

def recvjson(connection,recv_buffer=4096):
    buffer = b''
    while True:
        try:
            data = connection.recv(recv_buffer)
            if not data: raise ClientDisconnected('Client disconnected while receiving.')
            buffer += data
            return json.loads(buffer)
        except ValueError:
            pass

def hwserver_com(fn,*args):
    def com(msg):
        HW.sendall(bytes(msg,'utf-8')+b'\n')
        resp = json.loads(urllib.unquote_plus(recvline(HW)))
        if resp['error']:
            raise Exception('%s:\n%s'%(resp['response'],resp['traceback']))
        return resp['response']

    hello = urllib.quote_plus(json.dumps({'name':'wavemeter'}))
    msg = urllib.quote_plus(json.dumps({
                                            'function':fn,
                                            'args':args,
                                            'keep_alive':False
                                        }))
    HW = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    HW.settimeout(2)
    HW.connect((HW_IP,HW_PORT))
    try:
        com(hello)
        resp = com(msg)
    except:
        logger.exception('Error communicating to hwserver')
        raise
    finally:
        HW.close()
    return resp

# Server methods
def get_client():
    while True:
        try:
            client,ip = SERVER.accept()
            ip = ip[0] # Ignore port
            if ip not in settings.CHANS_USED:
                client.close()
                logger.exception('Client %s not configured in settings.CHANS_USED'%ip)
                continue
            TRANSMISSION_ID[ip] = 1
            return client,ip
        except KeyboardInterrupt:
            logger.debug('User aborted.')
            USER_EXIT = True
            return
        except socket.timeout:
            pass

def handle_client(client,ip):
    try:
        while True:
            if USER_EXIT: break
            msquared_req = recvjson(client)
            logger.debug('Request: '+json.dumps(msquared_req))
            try:
                hw_reqs = from_msquared(msquared_req,ip)
            except:
                logger.error(json.dumps(msquared_req))
                raise
            hw_resp = None
            for hw_req in hw_reqs:
                hw_resp = hwserver_com(*hw_req)
            msquared_resp = to_msquared(msquared_req,hw_resp,ip)
            logger.debug('Response: '+msquared_resp)
            client.sendall(bytes(msquared_resp.replace(' ',''),'utf-8'))
    except:  # Turn off channels
        for chan in settings.CHANS_USED[ip][0]:  # The 0 index is to select the channel tuple in the list
            hwserver_com('SetSwitcherSignalStates',chan,0,0)
        raise

def client_thread(client,ip):
    try:
        handle_client(client,ip)
    except KeyboardInterrupt:
        logger.debug('User aborted.')
        USER_EXIT = True
    except (socket.timeout,ClientDisconnected,ConnectionResetError):
        logger.info('Client disconnected')
    except:
        logger.exception('Unhandled error in main while loop')
    finally:
        client.close()

if __name__ == '__main__':
    try:
        t_start = time.time()
        while True:
            try:
                version = hwserver_com('GetVersion')
                break
            except:
                if time.time() - t_start < 60: # Give hwserver 60 seconds to startup
                    logger.warning('Failed to find wavemeter software version from hwserver, trying again in 5 seconds.')
                    time.sleep(5) # Try again in 5 seconds
                else:
                    logger.exception('Failed to find wavemeter software version from hwserver for 60 seconds. Aborting.')
                    raise
        logger.info('Found wavemeter software version: %i'%version)
        while True:  # main loop
            logger.info('Waiting for client.')
            client,ip = get_client()
            client.settimeout(5)
            logger.info('New client: %s'%ip[0])
            threading.Thread(target=client_thread,args=(client,ip)).start()
            if USER_EXIT: break
    finally:
        SERVER.close()
        logger.critical('Stopping server.')
