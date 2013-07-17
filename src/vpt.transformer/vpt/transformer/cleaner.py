"""
delete - module
delete all files and folder that too old

"""

from sys import argv
import datetime
import os
import shutil

def run_script():
	"""function to run script"""
	# set path of the directory to be cleaned
	path = os.path.dirname(os.path.abspath(argv[0]))
	path = os.path.join(path, 'transforms')

	# current time 
	now = datetime.datetime.now()
	print "current time:", now

	# change working the directory to directory to be cleaned
	os.chdir(path)

	# walk through the directory
	# if the files or folders are modified more than 24h00m before the moment this script start, it will be deleted
	for files in os.listdir(path):
		# check if the file's prefix is formatted as "%Y%m%d-%H%M%S"
		try:
			ftime = datetime.datetime.strptime(files[0:15], "%Y%m%d-%H%M%S")
		except ValueError:
			continue
			
		# compare time using delta
		delta = (now - ftime)
		
		# check if delta is greater than or equal 24h00m
		if delta.days >= 1:
			print "%r modified %s ago. Delete." % (files, delta)
			
			# it is, delete it
			# note that it could be directories or files. Check and appy action for each cases	
			if os.path.isdir(files):
				# using shutil.rmtree() instead of os.rmdir() to delete non-empty directory
				shutil.rmtree(files)
			elif os.path.isfile(files):
				os.remove(files)
			else:
				print "Error, not file or directory"

# script is only executed when call form command line, not when compiled
if __name__ == "__main__":
	run_script()
else:
	print "script is not called from main"	