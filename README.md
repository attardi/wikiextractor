# WikiExtractor
[WikiExtractor.py](http://medialab.di.unipi.it/wiki/Wikipedia_Extractor) is a Python script that extracts and cleans text from a [Wikipedia database dump](http://download.wikimedia.org/).

The tool is written in Python and requires Python 2.7 or Python 3.3+ but no additional library.

For further information, see the [project Home Page](http://medialab.di.unipi.it/wiki/Wikipedia_Extractor) or the [Wiki](https://github.com/attardi/wikiextractor/wiki).

# Wikipedia Cirrus Extractor

`cirrus-extractor.py` is a version of the script that performs extraction from a Wikipedia Cirrus dump.
Cirrus dumps contain text with already expanded templates.

Cirrus dumps are available at:
[cirrussearch](http://dumps.wikimedia.org/other/cirrussearch/).

# Details

WikiExtractor performs template expansion by preprocesssng the whole dump and extracting template definitions.

In order to speed up processing:

- multiprocessing is used for dealing with articles in parallel
- a cache is kept of parsed templates (only useful for repeated extractions).

## Installation

The script may be invoked directly, however it can be installed by doing:

    (sudo) python setup.py install

## Usage
The script is invoked with a Wikipedia dump file as an argument.
The output is stored in several files of similar size in a given directory.
Each file will contains several documents in this [document format](http://medialab.di.unipi.it/wiki/Document_Format).

    usage: WikiExtractor.py [-h] [-o OUTPUT] [-b n[KMG]] [-c] [--html] [-l] [-s]
                            [--lists] [-ns ns1,ns2] [-xns ns1,ns2]
                            [--templates TEMPLATES] [--no-templates] [--escapedoc]
                            [-r] [--min_text_length MIN_TEXT_LENGTH]
                            [--filter_disambig_pages] [--processes PROCESSES] [-q]
                            [--debug] [-a] [-v]
                            input

    Wikipedia Extractor:
    Extracts and cleans text from a Wikipedia database dump and stores output in a
    number of files of similar size in a given directory.
    Each file will contain several documents in the format:

        <doc id="" revid="" url="" title="">
            ...
            </doc>

    Template expansion requires preprocesssng first the whole dump and
    collecting template definitions.

    positional arguments:
      input                 XML wiki dump file

    optional arguments:
      -h, --help            show this help message and exit
      --processes PROCESSES number of processes to use (default: number of CPU cores)

    Output:
      -o OUTPUT, --output OUTPUT
                            directory for extracted files (or '-' for dumping to
                            stdout)
      -b n[KMG], --bytes n[KMG]
                            maximum bytes per output file (default 1M)
      -c, --compress        compress output files using bzip

    Processing:
      --html                produce HTML output, subsumes --links
      -l, --links           preserve links
      -s, --sections        preserve sections
      --lists               preserve lists
      -ns ns1,ns2, --namespaces ns1,ns2
                            accepted link namespaces
      -xns ns1,ns2, --xml_namespaces ns1,ns2
                            accepted page xml namespaces -- 0 for main/articles
      --templates TEMPLATES
                            use or create file containing templates
      --no-templates        Do not expand templates
      --escapedoc           use to escape the contents of the output
                            <doc>...</doc>
      -r, --revision        Include the document revision id (default=False)
      --min_text_length MIN_TEXT_LENGTH
                            Minimum expanded text length required to write
                            document (default=0)
      --filter_disambig_pages
                            Remove pages from output that contain disabmiguation
                            markup (default=False)

    Special:
      -q, --quiet           suppress reporting progress info
      --debug               print debug info
      -a, --article         analyze a file containing a single article (debug
                            option)
      -v, --version         print program version


Saving templates to a file will speed up performing extraction the next time,
assuming template definitions have not changed.

Option --no-templates significantly speeds up the extractor, avoiding the cost
of expanding [MediaWiki templates](https://www.mediawiki.org/wiki/Help:Templates).

For further information, visit [the documentation](http://attardi.github.io/wikiextractor).
