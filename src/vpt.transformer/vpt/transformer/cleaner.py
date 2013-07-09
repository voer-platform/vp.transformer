"""
delete - module
delete all files and folder that too old

"""

from sys import exit
from sys import argv
import datetime
import os
import shutil

# set path of transform file to be cleaned
path = os.path.dirname(argv[0])
path = os.path.join(path, 'transforms')

# current time 
now = datetime.datetime.now()
print "current time:", now

# change working directory to directory to be cleaned
os.chdir(path)

# walk through the directory
# if the files or folder is modified more than 24h00 before the moment start this script, it will be deleted
for files in os.listdir(os.getcwd()):
	# check if the file's prefix is formatted in "%Y%m%d-%H%M%S"
	try:
		ftime = datetime.datetime.strptime(files[0:15], "%Y%m%d-%H%M%S")
	except ValueError:
		continue
		
	# compare using delta
	delta = (now - ftime)
	
	# check if delta is greater or equal than 1 day
	if delta.days >= 1:
		print "%r modified %s ago. Delete." % (files, delta)
		
	# it is. Delete it.
		# note that it could be directory or files	
		if os.path.isdir(files):
			# using shutil.rmtree() instead of os.rmdir() to delete non-empty directory
			shutil.rmtree(files)
		elif os.path.isfile(files):
			os.remove(files)
		else:
			print "Error, not file or directory"