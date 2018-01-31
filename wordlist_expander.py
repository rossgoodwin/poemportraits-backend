import sys
import time
from socket_sender import WordCamera

wc = WordCamera(sentence_count=2, seed_ix=0, manual=False, looper=False)

with open(sys.argv[1]) as infile:
	words = filter(lambda y: y, map(lambda x: x.strip().lower(), infile.read().strip().split('\n')))

#print(len(list(words)))
#print(list(words))


for w in list(words):
	print(w)
	wc.capture(w)
	time.sleep(8)


