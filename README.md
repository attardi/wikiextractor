# wikiextractor
[WikiExtractor.py](http://medialab.di.unipi.it/wiki/Wikipedia_Extractor) is a Python script that extracts and cleans text from a [Wikipedia database dump](http://download.wikimedia.org/).

The tool is written in Python and requires no additional library.

For further information, see the [project Home Page](http://medialab.di.unipi.it/wiki/Wikipedia_Extractor) or the [Wiki](https://github.com/attardi/wikiextractor/wiki).

This is a beta version that performs template expansion by preprocesssng the whole dump and extracting template definitions.
The current version keeps a cache of parsed templates, achieving a speedup of twice over the previous version.

## Usage
The script is invoked with a Wikipedia dump file as an argument.
The output is stored in a number of files of similar size in a chosen directory.
Each file will contains several documents in this [document format](http://medialab.di.unipi.it/wiki/Document_Format).

    usage: WikiExtractor.py [-h] [-o OUTPUT] [-b n[KMG]] [-c] [--html] [-l]
			    [-ns ns1,ns2] [-s] [--templates TEMPLATES]
			    [--no-templates] [--processes PROCESSES] [-q] [--debug]
			    [-a] [-v]
			    input

    positional arguments:
      input                 XML wiki dump file; use '-' to read from stdin

    optional arguments:
      -h, --help            show this help message and exit
      --processes PROCESSES number of processes to use (default number of CPU cores)

    Output:
      -o OUTPUT, --output OUTPUT
			    output path; a file if no max bytes per file set, 
			    otherwise a directory to collect files. use '-' for stdout.
      -b n[KMG], --bytes n[KMG]
			    maximum bytes per output file (default is no limit: one file)
      -c, --compress        compress output files using bzip

    Processing:
      --html                produce HTML output, subsumes --links and --sections
      -l, --links           preserve links
      -ns ns1,ns2, --namespaces ns1,ns2
			    accepted namespaces
      -s, --sections        preserve sections
      --templates TEMPLATES
			    use or create file containing templates
      --no-templates        Do not expand templates

    Special:
      -q, --quiet           suppress reporting progress info
      --debug               print debug info
      -a, --article         analyze a file containing a single article (debug)
			    option
      -v, --version         print program version

Saving templates to a file will speed up performing extraction the next time,
assuming template definitions have not changed.

Option --no-templates significantly speeds up the extractor, avoiding the cost of expanding [MediaWiki templates](https://www.mediawiki.org/wiki/Help:Templates).

For further information, visit [the documentation](http://attardi.github.io/wikiextractor).

