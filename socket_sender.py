import pika
import sys
import os
import re
import time
import math
from datetime import datetime
import subprocess
from random import sample as rs, choice as rc, randint as ri
import threading
from collections import defaultdict
from hashids import Hashids
import shutil
import webbrowser
from pattern.en import referenced, parse, singularize

import asyncio
import websockets
# import razer_rgb
# import serial
# import thermal


class WordCamera(object):

    VALID_IMG = set(['jpg', 'jpeg', 'png'])

    def __init__(self, do_upload=False, img_orig_fp="", sentence_count=7, seed_ix=0, ebook_title="", ascii_img_path="", manual=False, looper=False, folderpath=""):
        self.do_upload = do_upload
        self.img_orig_fp = img_orig_fp
        self.manual = manual
        # ebook of results?
        # self.ebook = ebook
        self.ebook_title = ebook_title

        self.folderpath = folderpath

        # ascii img path
        self.ascii_img_path = ascii_img_path

        # word pool
        self.word_pool = list()

        # Connect to RabbitMQ
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost')
        )
        self.channel = self.connection.channel()

        possible_pre_seeds = [
            "The dreams of men who would regard the scene,\nThe sorrows of the morn, whose waters wave,\n",
            "~~~The arm of a person or thing and a frequency of a similar process within a postulated printed contest with the weapons of the post office.\n~|~",
            "The door opened and the old man turned in his armchair to see whether he had been to the river bank.\n"
        ]

        self.seed_ix = seed_ix
        self.pre_seed = possible_pre_seeds[self.seed_ix]

        # Serial to Arduino button
        # self.ser = serial.Serial('/dev/ttyACM0')

        # Queue names
        queue_names = [
            # 'ImgPaths',
            'Captions',
            'CaptionToExpand',
            'Expansions'
        ]

        # Declare and Purge Queues
        for qn in queue_names:
            self.channel.queue_declare(queue=qn)
            self.channel.queue_purge(queue=qn)

        # HashIds
        self.hashids = Hashids()

        self.cur_hash = None

        # Unused captions (changes every image)
        self.unused_captions = list()
        self.unused_captions_per_graf = 0

        # Class Variables
        self.sentence_count = sentence_count
        self.sentences = defaultdict(list)
        self.img_dest = '/home/ubuntu/poemportraits/img'
        # self.template_path = '/home/ubuntu/poemportraits/poembooth_template.html'
        # self.ebook_template_path = '/home/rg/projects/wc3/ebook_template.html'

        self.thr1 = threading.Thread(target=self.consume)
        self.thr1.daemon = True
        self.thr1.start()

        # loop = asyncio.get_event_loop()

        # self.thr2 = threading.Thread(target=self.socket_loop, args=(loop,))
        # self.thr2.daemon = True
        # self.thr2.start()


    # def socket_loop(self, loop):
    #     asyncio.set_event_loop(loop)
    #     start_server = websockets.serve(self.socket_handler, '0.0.0.0', 8081)
    #     asyncio.get_event_loop().run_until_complete(start_server)
    #     asyncio.get_event_loop().run_forever()

    # async def socket_handler(self, websocket, path):
    #     print("SOCKET HANDLER RUNNING!!")
    #     while 1:
    #         if self.sentences[self.cur_hash]:

    #             cur_sentence = self.sentences[self.cur_hash].pop()

    #             print("SENDING: %s" % cur_sentence)

    #             await websocket.send(cur_sentence)

    #         await asyncio.sleep(0.1)

    def process_fp(self):
        if self.img_orig_fp.rsplit('.').pop().strip().lower() in self.VALID_IMG:
            self.pre_narrate_individual(self.img_orig_fp)
        else:
            self.pre_narrate_folder()


    def capture(self, user_input):
        tokens = user_input.strip().split()

        if len(tokens) == 1:
            try:
                pos = parse(user_input).split()[0][0][1]
            except:
                pos = False

            if pos and pos.startswith('N'):
                if 'S' in pos:
                    user_input = singularize(user_input)
                user_input = rc([
                    referenced(user_input),
                    'that ' + user_input,
                    'this ' + user_input,
                    'your ' + user_input,
                    'the ' + user_input,
                    'our ' + user_input,
                    'my ' + user_input
                ])

        user_input += ' '

        img_hash = self.hashids.encode(int(time.time()*1000))
        self.cur_hash = img_hash

        # fn = "%s.jpg" % img_hash
        # filepath = os.path.join(self.img_dest, fn)
        # cmd_list = [
        #     'fswebcam', '-r', '640x480', '--jpeg', '75',
        #     '--no-banner', filepath
        # ]
        # proc = subprocess.Popen(cmd_list)
        # proc.communicate()

        # Narrate
        self.narrate(img_hash, user_input)

        return img_hash

    def img2txt(self, img_path):
        cmd_list = [
            '/usr/local/bin/img2txt.py', img_path, '--maxLen=80',
            '--targetAspect=0.4', '--bgcolor=#FFFFFF'
        ]
        proc = subprocess.Popen(cmd_list, stdout=subprocess.PIPE)
        result = proc.stdout.read()
        # thermal.basic_print(result)

    def narrate(self, img_hash, user_input):
        # Put printer in line print mode + feed paper
        # thermal.line_print_mode()
        # thermal.feed_paper()

        def int_to_enc(i):
            return "{0:b}".format(i).replace('0', '~').replace('1', '|')


        words_to_expand = [ user_input ]

        if len(self.word_pool) >= self.sentence_count-1:
            words_to_expand.extend( rs(self.word_pool, self.sentence_count-1) )
        elif not self.word_pool:
            words_to_expand.append( user_input )
        else:
            words_to_expand.extend(self.word_pool)

        # Add user's word to word pool for future iterations
        self.word_pool.append(user_input)

        def capitalize_first_char(s):
            return s[0].upper() + s[1:]

        final_words_to_expand = map(
            # lambda (i, x): ,
            lambda x: x[0].upper() + x[1:],
            words_to_expand
        )

        for c in final_words_to_expand:
            self.channel.basic_publish(
                exchange = '',
                routing_key = 'CaptionToExpand',
                body = img_hash + '#' + self.pre_seed + c
            )


    def approve(self, text):
        print('CANDIDATE: %s' % text)
        isApproved = raw_input('Approve? (y/n)\n')
        return isApproved and isApproved.strip().lower() != 'n'

    def consume(self):
        # Bind methods to consumption queues
        # self.channel.basic_consume(self.process_captions, queue='Captions')
        self.channel.basic_consume(self.process_expansions, queue='Expansions')

        # Go
        self.channel.start_consuming()


    def process_expansions(self, ch, method, properties, body):
        img_hash, expansion = body.decode('utf8').split('#', 1)
        # print(expansion)

        expansion = expansion[len(self.pre_seed):]
        
        grafs = expansion.strip().split('\n')

        # if len(grafs) > 1:
        #     first_graf = '\n'.join(grafs[:-1])
        # else:
        #     first_graf = grafs[0]

        first_graf = grafs[0]

        first_graf = first_graf.replace('|', '').replace('~', '').replace('<UNK>', '(?)')

        def split_on_punc(punc, graf):
            # changed from rsplit to split to make shorter sentences
            reg_exp = r'\b' + re.escape(punc) + r'\s'
            complete_sents_no_punc = re.split(reg_exp, graf, maxsplit=1)[0]
            complete_sents = complete_sents_no_punc + punc.strip()
            return complete_sents[0].upper() + complete_sents[1:]

        result = None

        all_punc_set = set(['.', '!', '?', ',', ';', ':'])

        # if len(grafs) > 1:
        #     result = first_graf[0].upper() + first_graf[1:]
        #     result = result.strip()
        #     if not result[-1] in all_punc_set:
        #         result += '.'

        results = list()

        if ', ' in first_graf:
            results.append(split_on_punc(',', first_graf))
        if ': ' in first_graf:
            results.append(split_on_punc(':', first_graf))
        if '; ' in first_graf:
            results.append(split_on_punc(';', first_graf))
        if '? ' in first_graf:
            results.append(split_on_punc('?', first_graf))
        if '! ' in first_graf:
            results.append(split_on_punc('!', first_graf))
        if '. ' in first_graf:
            results.append(split_on_punc('.', first_graf))
        if first_graf and first_graf[-1] in all_punc_set:
            results.append(first_graf[0].upper() + first_graf[1:])
        
        results.append(first_graf[0].upper() + first_graf[1:] + '...')
        # else:
        #     result = first_graf[0].upper() + first_graf[1:].rstrip() + '...'

        # if self.unused_captions and rc([True, False, False, False, False]):
        #     graf_captions = list()
        #     for _ in range(self.unused_captions_per_graf):
        #         graf_captions.append( self.unused_captions.pop() )
        #     graf = ', '.join(graf_captions)
        #     self.sentences[img_hash].append( graf[0].upper() + graf[1:] + '.' )

        result = min(results, key=len)


        # print "MAIN BLOCK RUNNING"

        approved = True

        if self.manual:
            approved = self.approve(result)

        if approved:
            # print "APPEND RESULT TO SENTENCES"
            print(result)
            self.sentences[img_hash].append(result)
            print(self.sentences[img_hash])



            with open(os.path.join('/home/ubuntu/poemportraits/pages', img_hash+'.txt'), 'a') as outfile:
                outfile.write(result+'\n')
            # thermal.thermal_print(result)
            # thermal.line_break()
        # else:
        #     self.sentences[img_hash].append("")

        # if self.looper and ( len(self.sentences[img_hash]) >= self.sentence_count or len(self.sentences[img_hash]) > len(self.word_pool) ):
        #     self.publish(img_hash)


        print(img_hash, len(self.sentences[img_hash]))

    def get_text(self, img_hash):
        return ' '.join(self.sentences[img_hash])

    def change_sentence_count(self, new_count):
        self.sentence_count = new_count




if __name__ == '__main__':
    wc = WordCamera(sentence_count=2, seed_ix=0, manual=False, looper=False)
    wc.capture("oceans")
    # time.sleep(8)
    wc.capture("land")
    # time.sleep(8)
    wc.capture("sun")





