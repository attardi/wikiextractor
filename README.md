# WikiExtractor
[WikiExtractor.py](http://medialab.di.unipi.it/wiki/Wikipedia_Extractor) is a Python script that extracts and cleans text from a [Wikipedia database dump](http://download.wikimedia.org/).

The tool is written in Python and requires Python 2.7 or Python 3.3+ but no additional library. Python 2 may not work properly any longer, testing may be needed.

For further information, see the [project Home Page](http://medialab.di.unipi.it/wiki/Wikipedia_Extractor) or the [Wiki](https://github.com/attardi/wikiextractor/wiki).

# Wikipedia Cirrus Extractor

`cirrus-extractor.py` is a version of the script that performs extraction from a Wikipedia Cirrus dump.
Cirrus dumps contain text with already expanded templates.

Cirrus dumps are available at:
[cirrussearch](http://dumps.wikimedia.org/other/cirrussearch/).

# Details

WikiExtractor performs template expansion by preprocessing the whole dump and extracting template definitions.

In order to speed up processing:

- multiprocessing is used for dealing with articles in parallel
- a cache is kept of parsed templates (only useful for repeated extractions).

## Installation

Currently no installation. The script may be invoked directly.

## Usage
The script is invoked with a Wikipedia dump file as an argument.
The output is stored in several files of similar size in a given directory.
Each file will contains several documents in this [document format](http://medialab.di.unipi.it/wiki/Document_Format).

usage: WikiExtractor.py <br>
                        [-h] [-o OUTPUT] [-b n[KMG]] [-c] [--json] [--html]<br>
                        [-l] [-s] [--headersfooters] [--noLineAfterHeader]<br>
                        [-no-title] [--squeeze_blank] [--for-bert]<br>
                        [--remove-special-tokens] [--remove-html-tags]<br>
                        [--point-separated]<br>
                        [--restrict_pages_to RESTRICT_PAGES_TO]<br>
                        [--max_articles MAX_ARTICLES] [--verbose] [--lists]<br>
                        [-ns ns1,ns2] [--templates TEMPLATES] [--no-templates]<br>
                        [-r] [--min_text_length MIN_TEXT_LENGTH]<br>
                        [--filter_disambig_pages] [-it abbr,b,big]<br>
                        [-de gallery,timeline,noinclude] [--keep_tables]<br>
                        [--processes PROCESSES] [-q] [--debug] [-a]<br>
                        [--log_file LOG_FILE] [-v]<br>
                        [--filter_category FILTER_CATEGORY]<br>
                        input

## Examples (tested for "correct" output)
<b>Debug and testing (short and fast):</b>
python3 WikiExtractor.py -o wiki/test --templates templat.txt --max_articles 10 --verbose wiki/wiki-20191101-pages-articles.xml

<b>JSON (most extracted information):</b>
python3 WikiExtractor.py -o wiki/test --filter_disambig_pages --templates templat.txt --titlefree --json --min_text_length 100 wiki/wiki-20191101-pages-articles.xml<br>
python3 WikiExtractor.py -o wiki/test --filter_disambig_pages --templates templat.txt --json --for-bert --min_text_length 100 wiki/wiki-20191101-pages-articles.xml

<b>Text only with "extra cleaning" (change --min_text_length to suit your use cases):</b>
python3 WikiExtractor.py -o wiki/test --filter_disambig_pages --no_templates --remove-html-tags --remove-special-tokens --min_text_length 100 wiki/wiki-20191101-pages-articles.xml

<b>Other combinations:</b>
python3 WikiExtractor.py -o wiki/test --headersfooters --titlefree --squeeze-blank wiki/wiki-20191101-pages-articles.xml<br>
python3 WikiExtractor.py -o wiki/test --titlefree --squeeze-blank wiki/wiki-20191101-pages-articles.xml<br>
python3 WikiExtractor.py -o wiki/test --noLineAfterHeader --squeeze-blank wiki/wiki-20191101-pages-articles.xml<br>
python3 WikiExtractor.py -o wiki/test --for-bert wiki/wiki-20191101-pages-articles.xml<br>
python3 WikiExtractor.py -o wiki/test --filter_disambig_pages --no_templates --for-bert --min_text_length 100 wiki/wiki-20191101-pages-articles.xml<br>
python3 WikiExtractor.py -o wiki/test --filter_disambig_pages --templates templat.txt --titlefree --json --for-bert --min_text_length 100 wiki/wiki-20191101-pages-articles.xml<br>
python3 WikiExtractor.py -o wiki/test --filter_disambig_pages --templates templat.txt --squeeze-blank --titlefree --max_articles 10 --remove-html-tags --min_text_length 100 wiki/wiki-20191101-pages-articles.xml<br>

<b>Postprocessing</b>
After running the extractor there may be a need for cleaning the output. In linux you may use any of the following examples. Please copy all the files to a safe place first. ANY ERROR IN THE CODE WILL DESTROY YOUR TEXT. You can be sure your text will be destroyed many times before you find the right cleaning scripts.<br>
left trim on one file: sed -i 's/^[ ]*//g' YOURTEXT<br>
right trim on one file: sed -i 's/[ ]*$//g' YOURTEXT<br>
If you want to work many files at a time use (do NOT have any othe files in the folder or subfolders):<br>
left trim on all files in folder or subfolder: find wiki/* -type f -exec sed -i 's/^[ ]*//g' {} \;<br>
right trim on all files in folder or subfolder: find wiki/* -type f -exec sed -i 's/[ ]*$//g' {} \;<br>
remove a line that starts with < and ends with > on all files in folder or subfolder: find wiki/* -type f -exec sed -E -i '/^<[^<]*>$/d' {} \;<br>
remove a line that starts with ( and ends with ) on all files in folder or subfolder: find wiki/* -type f -exec sed -E -i '/^[(][^(]*[)]$/d' {} \;<br>
Search Internet for variations and how to use with other operating systems. One variation would be to remove option "-i" and write changes to new files, instead of -i[nline] - although not very useful if you do more than one cleaning operation.

For those use cases where only on large file is needed, in linux use: cat --squeeze-blank wiki/\*/\* > wiki/wiki.txt



    Wikipedia Extractor:
    Extracts and cleans text from a Wikipedia database dump and stores output in a
    number of files of similar size in a given directory.
    Each file will contain several documents in the format:

        <doc id="" revid="" url="" title="">
            ...
            </doc>

    If the program is invoked with the --json flag, then each file will
    contain several documents formatted as json ojects, one per line, with
    the following structure

        {"id": "", "revid": "", "url":"", "title": "", "text": "..."}

    Template expansion requires preprocesssng first the whole dump and
    collecting template definitions.

    positional arguments:
      input                 XML wiki dump file

    optional arguments:
      -h, --help            show this help message and exit
      --processes PROCESSES
                            Number of processes to use (default 1)

    Output:
      -o OUTPUT, --output OUTPUT
                            directory for extracted files (or '-' for dumping to
                            stdout)
      -b n[KMG], --bytes n[KMG]
                            maximum bytes per output file (default 1M)
      -c, --compress        compress output files using bzip
      --json                write output in json format instead of the default one

    Processing:
      --html                produce HTML output, subsumes --links
      -l, --links           preserve links
      -s, --sections        preserve sections
      --lists               preserve lists
      -ns ns1,ns2, --namespaces ns1,ns2
                            accepted namespaces in links
      --templates TEMPLATES
                            use or create file containing templates
      --no-templates        Do not expand templates
      -r, --revision        Include the document revision id (default=False)
      --min_text_length MIN_TEXT_LENGTH
                            Minimum expanded text length required to write
                            document (default=0)
      --filter_category path_of_categories_file
                            Include or exclude specific categories from the dataset. Specify the categories in
                            file 'path_of_categories_file'. Format:
                            One category one line, and if the line starts with:
                                1) #: Comments, ignored;
                                2) ^: the categories will be in excluding-categories
                                3) others: the categories will be in including-categories.
                            Priority:
                                1) If excluding-categories is not empty, and any category of a page exists in excluding-categories, the page will be excluded; else
                                2) If including-categories is not empty, and no category of a page exists in including-categories, the page will be excluded; else
                                3) the page will be included

      --filter_disambig_pages
                            Remove pages from output that contain disabmiguation
                            markup (default=False)
      -it abbr,b,big, --ignored_tags abbr,b,big
                            comma separated list of tags that will be dropped,
                            keeping their content
      -de gallery,timeline,noinclude, --discard_elements gallery,timeline,noinclude
                            comma separated list of elements that will be removed
                            from the article text
      --keep_tables         Preserve tables in the output article text
                            (default=False)
      --headersfooters      Adds header and footer to each article
                            (default=False)
      --noLineAfterHeader   Does not add line below title. Title is directly on article.
                            (default=False)
      --titlefree           No titles on articles
                            (default=False)
      --squeeze-blank       Minimize empty lines, that is, only empty lines are before/after title.
                            (default=False)

    Special:
      -q, --quiet           suppress reporting progress info
      --debug               print debug info
      -a, --article         analyze a file containing a single article (debug
                            option)
      -v, --version         print program version
      --log_file            specify a file to save the log information.


Saving templates to a file will speed up performing extraction the next time,
assuming template definitions have not changed.

Option --no-templates significantly speeds up the extractor, avoiding the cost
of expanding [MediaWiki templates](https://www.mediawiki.org/wiki/Help:Templates).

For further information, visit [the documentation](http://attardi.github.io/wikiextractor).
