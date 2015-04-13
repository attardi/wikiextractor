#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# =============================================================================
#  Version: 2.8 (Jan 10, 2015)
#  Author: Giuseppe Attardi (attardi@di.unipi.it), University of Pisa

# =============================================================================
#  Copyright (c) 2009. Giuseppe Attardi (attardi@di.unipi.it).
# =============================================================================
#  This file is part of Tanl.
#
#  Tanl is free software; you can redistribute it and/or modify it
#  under the terms of the GNU General Public License, version 3,
#  as published by the Free Software Foundation.
#
#  Tanl is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
# =============================================================================

"""Wikipedia Page Extractor:
Extracts a single page from a Wikipedia dump file.
"""

import sys, os.path
import re, random
import argparse
from itertools import izip
import logging, traceback
import urllib
import bz2, gzip
from htmlentitydefs import name2codepoint
import Queue, threading, multiprocessing


# Program version
version = '2.8'

# ----------------------------------------------------------------------
# READER

tagRE = re.compile(r'(.*?)<(/?\w+)[^>]*>(?:([^<]*)(<.*?>)?)?')
#tagRE = re.compile(r'(.*?)<(/?\w+)[^>]*>([^<]*)')
#                    1     2            3

def process_data(input_file, id, templates=False):
    """
    :param input_file: name of the wikipedia dump file.
    :param id: article id
    """

    if input_file.lower().endswith("bz2"):
        opener = bz2.BZ2File
    else:
        opener = open

    input = opener(input_file)

    page = []
    for line in input:
        line = line.decode('utf-8')
        if '<' not in line:         # faster than doing re.search()
            if page:
                page.append(line)
            continue
        m = tagRE.search(line)
        if not m:
            continue
        tag = m.group(2)
        if tag == 'page':
            page = []
            page.append(line)
            inArticle = False
        elif tag == 'id':
            curid = m.group(3)
            if id == curid:
                page.append(line)
                inArticle = True
            elif not inArticle and not templates:
                page = []
        elif tag == 'title':
            if templates:
                if m.group(3).startswith('Template:'):
                    page.append(line)
                else:
                    page = []
            else:
                page.append(line)
        elif tag == '/page':
            if page:
                page.append(line)
                print ''.join(page).encode('utf-8')
                if not templates:
                    break
            page = []
        elif page:
            page.append(line)

    input.close()

def main():
    parser = argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]),
        formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=__doc__)
    parser.add_argument("input",
                        help="XML wiki dump file")
    parser.add_argument("--id", default="",
                        help="article number")
    parser.add_argument("--template", action="store_true",
                        help="template number")
    parser.add_argument("-v", "--version", action="version",
                        version='%(prog)s ' + version,
                        help="print program version")

    args = parser.parse_args()

    process_data(args.input, args.id, args.template)

if __name__ == '__main__':
    main()
