import os
import re
import sys

fileToOpen = "testcase.css"
fileToWrite = "output.css"

# get drag and drop file from Explorer
if sys.argv[1]:
	fileToOpen = sys.argv[1]

replacements = [
	# comments
	[r'\/\*.*?\*\/', r''],
	# whitespace in selectors
	[r',\s*', r','],
	[r'([}][^{]*?)\s*([>~+])\s*', r'\1\2'],
	# whitespace around rulesets 
	[r'\s*{\s*', r'{'],
	[r'\s*}\s*', r'}'],
	# whitespace within rulesets
	[r'({[^}]*?[:,])[\s\n]+', r'\1'],
	[r'({[^}]*?)(;[^:}]*?)\s+([^:}]*?)', r'\1\2\3'],
	[r'({[^}]*?)\s*!important', r'\1!important'],
	# whitespace at start
	[r'^\s*', r''],
	# whitespace at end
	[r'\s*$', r''],
	# modify pseudo elements
	[r'::(before|after)', r':\1']
]

format = 'utf-8'

contents = open(fileToOpen, mode='r', encoding=format).read()
sizeBefore = len(contents)
with open(fileToWrite, 'w+', encoding=format) as file:
	iterations = 0
	while True:
		iterations += 1
		oldContents = contents
		for pair in replacements:
			contents = re.sub(pair[0], pair[1], contents, flags=re.DOTALL)
			#if '#mal_control_striptd' in contents:
			#	print(pair[0])
			#	break
		# continue only when no changes have been made
		if oldContents == contents:
			break

	file.write(contents)

	sizeAfter = len(contents)
	try:
		percent = 100 - round(sizeAfter / sizeBefore * 100)
		print(f'Minification complete in {iterations} passes. Sizes: {sizeBefore}/{sizeAfter} Reduction: {percent}%')
	except:
		print('Error calculating minification. Perhaps none occured?')