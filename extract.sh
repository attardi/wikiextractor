#!/bin/bash
#
# NOTES
#
# - Must expand templates to avoid a large loss of content.
# - Text will not (redundantly) contain the title string.
# - Keep sections. Section title will be marked by "Section::::".
# - Keep lists. List bullets will be marked by "BULLET::::".
# - Keep tables. They're mostly garbage but can be removed later (remove "^!*").
# - Remove disambiguation pages. Right now there is no use for them.

INPUT=$1
PROCESSES=$2
TEMPLATES=$3
OUTPUT=$4


#tests the return code of  wikiextractor to valid if cmd is installed
if ! command -v wikiextractor &> /dev/null
then

    echo "WikiExtractor is not installed. Please install it to use the script."
    echo "More details on the installation process can be found in README."
    exit 1
fi

wikiextractor $INPUT \
       --json \
       --processes $PROCESSES \
       --templates $TEMPLATES \
       --output $OUTPUT \
       --bytes 1M \
       --compress \
       --links \
       --sections \
       --lists \
       --keep_tables \
       --min_text_length 0 \
       --filter_disambig_pages
