# wikiextractor
[WikiExtractor.py](http://medialab.di.unipi.it/wiki/Wikipedia_Extractor) is a Python script that extracts and cleans text from a [Wikipedia database dump](http://download.wikimedia.org/).

The tool is written in Python and requires no additional library.

For further information, see the [project Home Page](http://medialab.di.unipi.it/wiki/Wikipedia_Extractor) or the [Wiki](https://github.com/attardi/wikiextractor/wiki).

The current beta version of WikiExtrctor.py is capable of performing template expansion to some extent.

## Usage
The script is invoked with a Wikipedia dump file as an argument.
The output is stored in a number of files of similar size in a chosen directory.
Each file will contains several documents in this [document format](http://medialab.di.unipi.it/wiki/Document_Format).

This is a beta version that performs template expansion by preprocesssng the
whole dump and extracting template definitions.

    Usage:
     WikiExtractor.py [options] xml-dump-file
      
    optional arguments:
      -h, --help            show this help message and exit
      -o OUTPUT, --output OUTPUT
                            output directory
      -b n[KM], --bytes n[KM]
                        put specified bytes per output file (default is 1M)
      -B BASE, --base BASE  base URL for the Wikipedia pages
      -c, --compress        compress output files using bzip
      -l, --links           preserve links
      -ns ns1,ns2, --namespaces ns1,ns2
                            accepted namespaces
      -q, --quiet           suppress reporting progress info
      --debug               print debug info
      -s, --sections        preserve sections
      -a, --article         analyze a file containing a single article
      --templates TEMPLATES
                            use or create file containing templates
      --no-templates        Do not expand templates
      --threads THREADS     Number of threads to use (default 8)
      -v, --version         print program version

Saving templates to a file will speed up performing extraction the next time,
assuming template definitions have not changed.

