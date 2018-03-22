#!/bin/bash

WikiExtractor.py \
/scratch/wikipedia-base/dumps/dump02212018/enwiki-latest-pages-articles.xml.bz2 \
--processes $1 \
--output /scratch/wikipedia-base/extracted/json-not-expanded \
--bytes 10M \
--compress \
--json \
--links \
--sections \
--lists \
--no-templates \
--min_text_length 0 \
--filter_disambig_pages \
--keep_tables
