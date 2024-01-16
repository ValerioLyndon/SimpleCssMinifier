import os
import re
import sys
import json
import subprocess

format = 'utf-8'

def replaceAll(text, replacements):
	for pair in replacements:
		text = re.sub(pair[0], pair[1], text, flags=re.DOTALL)
	return text

# process layers that contain rulesets such as:
# the main document, media queries, layers, containers, and keyframes
def processLayer(text):
	# do not change the order of these without thinking first or you may fuck something
	replacements = [
		# comments
		[r'\/\*.*?\*\/', r''],
		# trim whitespace at ends
		[r'^\s+|\s+$', r''],
		# modify pseudo elements
		[r'::(before|after)', r':\1'],
		# whitespace around blocks
		[r'\s*{\s*', r'{'],
		[r'\s*}\s*', r'}'],
		# selector whitespace (commas)
		[r'(}[^{]*,)\s+([^{]*{)', r'\1\2'],
		[r'^([^{]*,)\s+([^{]*{)', r'\1\2'],
		# selector modifiers
		[r'([}][^{]*?)\s*([>~+])\s*', r'\1\2'],
		# remove empty rulesets
		[r'[^}]+{}', r''],
		# replace newlines from is, has, etc selectors. This is flawed because
		# it could affect properties and it doesn't account for sub-levels
		# of selectors but for now we're calling it fine
		[r'(:(?:[a-z-]+\()[^)]*?)\n', r'\1'],
		# empty lines (this should always be the last cleanup step)
		[r'\n\r?\s*\n\r?', r''],
	]

	text = replaceAll(text, replacements)

	# find sub blocks
	# we're trying to recreate this regex:
	# @(?:media|container|layer|keyframes|scope|supports)[^;{]*?{
	# todo: make this shit match @font-face and other stuff you don't use often
	blockType = 'ruleset'
	insideType = False
	blockStart = 0
	blockEnd = 0
	blockText = ''
	insideBlock = False
	stringType = ''
	insideString = False
	i = -1
	depth = 0
	while i+1 < len(text):
		i += 1

		# ignore almost all other rules if we're inside a string
		if insideString:
			if text[i] == stringType and text[i-1] != '\\':
				insideString = False
			continue
		
		# if we're inside a child block, such as a ruleset, then separate it out
		# to process in another function while ignoring other rules
		elif insideBlock:
			# this code keeps going until it finds the end of the block
			if text[i] == '{':
				depth += 1
			elif text[i] == '}':
				depth -= 1
			if depth > -1:
				continue

			# we continue from here once we reached the block end
			blockEnd = i
			block = text[blockStart:blockEnd]
			if blockType == 'ruleset':
				newBlock = processRuleset(block)
			else:
				newBlock = processLayer(block)
			text = text[0:blockStart] + newBlock + text[blockEnd:len(text)]
			i -= len(block) - len(newBlock)
			
			# reset as we go back to parent codes
			insideBlock = False
			blockType = 'ruleset'
		
		elif insideType:
			# exit if no longer in alphanumeric text[i]acter
			if text[i] == '{' or text[i] ==';':
				insideType = False
		
		if text[i] == '@':
			type = re.match(r'(media|container|layer|keyframes|scope|supports).*?', text[i+1:i+10])
			if type != None:
				blockType = type[0]
				insideType = True
		elif text[i] == '{':
			blockStart = i+1
			insideBlock = True
			insideType = False
			depth = 0
		elif text[i] == "'" or text[i] == '"':
			stringType = text[i]
			insideString = True

	return text


def processRuleset(ruleset):
	# this will definitely have issues with semi colons in content text etc. Need to solve for this
	input_rules = ruleset.split(';')
	output_rules = []
	
	for rule in input_rules:
		if len(rule) == 0:
			continue
		# everything before first colon is the property. Everything after is the value
		split = rule.split(':')
		property = split.pop(0)
		value = ':'.join(split)
		output_rules.append(':'.join([
			processProperty(property),
			processValue(value)
		]))

	return ';'.join(output_rules)
	
def processProperty(property):
	return property.strip()
	
def processValue(value):
	replacements = [
		# !important markers
		[r'\s*(:|(?:!\s*important\s*)?)\s*$', r'\1'],
	]
	
	value = replaceAll(value, replacements)
	
	return value.strip()

def minify(text):
	iterations = 0
	while True:
		iterations += 1
		oldText = text
		
		text = processLayer(text)
		
		# continue only when no changes have been made
		if oldText == text:
			return text

def process_scm_file(file_path):
	with open(file_path, 'r') as f:
		data = json.load(f)

	input_file = os.path.join(os.path.dirname(file_path), data.get('in'))
	output_file = os.path.join(os.path.dirname(file_path), data.get('out'))
	min_repl = data.get('minify')
	reg_repl = data.get('replace')
	
	process_file(input_file, output_file, min_repl, reg_repl)

def process_directory(directory):
	for root, dirs, files in os.walk(directory):
		for file in files:
			if file == 'scm.json' or file.endswith('.scm.json'):
				file_path = os.path.join(root, file)
				process_scm_file(file_path)
			
def minify_capture_groups(match):
	if len(match.groups()) == 0:
		return minify(match.group(0))
	
	out = match.group(0)
	out = out.replace(match.group(1), minify(match.group(1)))
	return out
			
def process_file(input_path, output_path, min_repl, reg_repl):
	if min_repl == None:
		min_repl = ["^[\s\S]+$"]
	if reg_repl == None:
		reg_repl = []
	
	with open(input_path, mode='r', encoding=format) as input_file:
		output = input_file.read()
	sizeBefore = len(output)
	
	with open(output_path, 'w+', encoding=format) as output_file:
		# replace non-minified sections
		for pattern, replacement in reg_repl:
			output = re.sub(pattern, replacement, output)
	
		# send to minify function to get whittled down
		for pattern in min_repl:
			output = re.sub(pattern, minify_capture_groups, output)

		output_file.write(output)

		sizeAfter = len(output)
		try:
			percent = 100 - round(sizeAfter / sizeBefore * 100)
			print(f'Minification complete. Sizes: {sizeBefore}/{sizeAfter} Reduction: {percent}%')
		except:
			print('Error calculating minification. Perhaps none occured?')

if __name__ == "__main__":
	if len(sys.argv) > 1:
		input_path = sys.argv[1]
		if os.path.isfile(input_path):
			if len(sys.argv) > 2:
				output_path = sys.argv[2]
				process_file(input_path, output_path)
			else:
				raise 'If the first argument is a file then there must be an output argument provided.'
		elif os.path.isdir(input_path):
			process_directory(input_path)
		else:
			raise 'Argument not recognised as path.'
	else:
		raise 'No arguments provided..'
