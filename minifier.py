import os
import re
import sys

fileToOpen = "temp.nfp.css"
fileToWrite = "output.css"

# get drag and drop file from Explorer
if len(sys.argv) > 1:
	fileToOpen = sys.argv[1]

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
	replacements = [
		# space between properties
		[r'\s*(:|(?:!important\s*)?;)\s*', r'\1'],
		# ending semi-colons
		[r';$', r''],
	]

	ruleset = replaceAll(ruleset, replacements)

	return ruleset

def main():
	contents = open(fileToOpen, mode='r', encoding=format).read()
	sizeBefore = len(contents)
	with open(fileToWrite, 'w+', encoding=format) as file:
		iterations = 0
		while True:
			iterations += 1
			oldContents = contents
			contents = processLayer(contents);
			# continue only when no changes have been made
			if oldContents == contents:
				break

		file.write(contents)

		sizeAfter = len(contents)
		try:
			percent = 100 - round(sizeAfter / sizeBefore * 100)
			print(f'Minification complete after {iterations} iterations. Sizes: {sizeBefore}/{sizeAfter} Reduction: {percent}%')
		except:
			print('Error calculating minification. Perhaps none occured?')

if __name__ == '__main__':
	main()