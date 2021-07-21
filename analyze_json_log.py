import json, os, sys, time

if os.name == 'nt': # Windows
    class bcolors:
        HEADER = ''
        OKBLUE = ''
        OKGREEN = ''
        WARNING = ''
        FAIL = ''
        ENDC = ''
        BOLD = ''
        UNDERLINE = ''
else:
    class bcolors:
        HEADER = '\033[95m'
        OKBLUE = '\033[94m'
        OKGREEN = '\033[92m'
        WARNING = '\033[93m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'

filename = 'man_in_the_middle.log'
tstart = 0
def format(line,tstart=0):
    line = json.loads(line)
    t = line['created'] - tstart
    try:
        msquared = json.loads(line['msg'][1:])
        op = msquared['message']['op']
        txt = '{0:05d}: {1}'.format(int(round(t)),op)
        if op == 'set_w_meter_channel':
            txt += ' '+str(msquared['message']['parameters']['channel'][0])
        elif op == 'lock_wave_m_fixed':
            txt += ' '+str(msquared['message']['parameters']['lock_wavelength'][0])+' nm'
        elif op == 'lock_wave_m':
            txt += ' '+msquared['message']['parameters']['operation']
        elif op == 'set_wave_m':
            txt += ' '+str(msquared['message']['parameters']['wavelength'][0]) + ' nm'

        if 'f_r' in op or 'reply' in op:
            print bcolors.WARNING+txt+bcolors.ENDC
        else:
            print bcolors.OKGREEN+txt+bcolors.ENDC
    except:
        if 'New client' in line['msg']:
            tstart = line['created']
            t = line['created'] - tstart
            print ''
        txt = '{0:05d}: {1}'.format(int(round(t)),line['msg'].strip())
        if 'Traceback' in txt:
            print bcolors.FAIL+txt+bcolors.ENDC
        elif 'Ext:' in txt:
            print bcolors.OKBLUE+txt+bcolors.ENDC
        else:
            print txt
    return tstart

fseek = 0
with open(filename,'r') as f:
    while True:
        where = f.tell()
        line = f.readline()
        if line:
            tstart = format(line,tstart)
        else:
            f.seek(where)
            time.sleep(0.5)
