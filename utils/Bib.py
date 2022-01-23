import sys
import time

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter
import json
import re
import os
class Bib:
    # Assume that bib_string has valid structure
    def __init__(self, args):
        self.args = args
        self.dictionary={}
        self.bib_database = None
        self.index=0
        self.pattern_list = self.read_pattern_config()

    def get_bib_text(self):
        return bibtexparser.dumps(self.bib_database)

    def read_pattern_config(self):
        pattern_list={}
        if os.path.isdir(self.args.config_path):
            for root, ds, fs in os.walk(self.args.config_path):
                for f in fs:
                    with open(os.path.join(root, f), "r", encoding='utf-8') as f:
                        pattern_list.update(json.loads(f.read()))
        else:
            with open(self.args.config_path, "r", encoding='utf-8') as f:
                pattern_list = json.loads(f.read())
        return pattern_list

    def process_bar(self,percent, start_str='', end_str='', total_length=0):
        # bar = ''.join(["\033[31m%s\033[0m" % '   '] * int(percent * total_length)) + ''
        # bar = '\r' + start_str + bar.ljust(total_length) + ' {:0>4.1f}%|'.format(percent * 100) + end_str
        # print(bar, end='', flush=True)
        # sys.stdout.write(bar)
        print("\r", end="")
        i=int(percent*100)
        print("█" * (i // 2), "|Writing: {}%|100% ".format(i), end="")
        sys.stdout.flush()

    def __simplify_bib__(self,item):
        if 'archiveprefix' in item:
            item['archivePrefix'] = item['archiveprefix']
            del item['archiveprefix']
            if 'primaryclass' in item:
                item['primaryClass'] = item['primaryclass']
                del item['primaryclass']
            return item
        if 'author' not in item:
            return item
        temp_item = {'ENTRYTYPE': item['ENTRYTYPE'],
                     'ID': item['ID'],
                     'author': item['author'],
                     'title': item['title'], }
        if 'year' in item:
            temp_item['year'] = item['year']
        if item['ENTRYTYPE'] == 'book':
            if 'address' in item:
                temp_item['address'] = item['address']
            if 'publisher' in item:
                temp_item['publisher'] = item['publisher']
            return temp_item
        if 'booktitle' in item:
            booktitle = item['booktitle'].replace('\n', ' ').replace('\&', 'and')
            booktitle = booktitle.replace('{', '').replace('}', '').replace('  ', ' ').replace('[', '').replace(']', '')
            for key in self.pattern_list.keys():
                m = re.search(key.lower(), booktitle.lower())
                if m is not None:
                    booktitle = 'Proc. of ' + self.pattern_list[key]
                    break
            temp_item['booktitle'] = booktitle

        if 'journal' in item:
            journal=item['journal']
            temp = journal.replace('\n', ' ')
            temp = temp.replace('{', '').replace('}', '').replace('  ', ' ').replace('[', '').replace(']', '')
            if temp.lower()=='advances in neural information processing systems':
                journal='Proc. of NeurIPS'
            else:
                m = re.search('AAAI', journal)
                if m is not None:
                    journal = 'Proc. of AAAI'

            temp_item['journal'] = journal
            return temp_item
        return temp_item

    def mark_duplicate(self,item):
        if item['title'].lower() in self.dictionary:
            temp_index = self.index
            if 'booktitle' in item or ('journal' in item and not item['journal'].lower().find('arxiv')>=0):
                temp_index = self.dictionary[item['title'].lower()]
            self.bib_database.entries[temp_index] = '#'
        else:
            self.dictionary[item['title'].lower()] = self.index

    def simplify_bib(self,bib_string):
        parser = BibTexParser(common_strings=True)
        parser.ignore_nonstandard_types = True

        if self.bib_database is None:
            self.bib_database = bibtexparser.loads(bib_string, parser=parser)
        else:
            self.bib_database.entries += bibtexparser.loads(bib_string, parser=parser).entries

        while self.index < len(self.bib_database.entries):
            item=self.bib_database.entries[self.index]
            self.bib_database.entries[self.index]=self.__simplify_bib__(item)
            if self.args.remove_duplicate:
                self.mark_duplicate(item)
            self.index += 1
        if self.args.remove_duplicate:
            self.bib_database.entries=[x for x in self.bib_database.entries if x != '#']

    def write_to_file(self):
        writer = BibTexWriter()
        print("Writing...")
        with open(self.args.output_path, 'a', encoding='utf-8') as bibfile:
            bibfile.write(writer.write(self.bib_database))
        print("Finished...")