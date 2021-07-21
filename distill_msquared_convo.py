import json, sys, glob, os

fname = sys.argv[1]

if os.path.splitext(fname)[0]:
	fname = os.path.join(fname,'*.txt')
files = glob.glob(fname)

tasks = {}
ips = {}
for file in files:
	print 'Reading: %s'%file
	with open(file,'r') as f:
		for line in f.readlines():
			try:
				jline = json.loads(line)
				task = jline['message']['transmission']['task1']
				params = ''
				if 'parameters' in task:
					params = json.dumps(task['parameters'])
				if task['name'] not in tasks:
					tasks[task['name']] = [params]
				elif params not in tasks[task['name']]:
					tasks[task['name']] += [params]
				if task['name'] == 'start-link':
					ip = task['parameters']['ip-address']
					if ip in ips:
						ips[ip] += 1
					else:
						ips[ip] = 1
			except:
				print line
				raise

for item in ips.keys():
	print '%s: %s\n'%(item,ips[item])

for item in tasks.keys():
	if '-reply' not in item:
		print '%s:\n  %s'%(item,'\n  '.join(tasks[item]))
		try:
			replies = tasks[item+'-reply']
			print '%s:\n  %s'%(item+'-reply','\n  '.join(replies))
		except KeyError:
			pass
	print ''
		
