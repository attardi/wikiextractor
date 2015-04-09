#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# =============================================================================
#  Version: 2.8 (Jan 10, 2015)
#  Author: Giuseppe Attardi (attardi@di.unipi.it), University of Pisa
#	   Antonio Fuschetto (fuschett@di.unipi.it), University of Pisa
#
#  Contributors:
#	Leonardo Souza (lsouza@amtera.com.br)
#	Juan Manuel Caicedo (juan@cavorite.com)
#	Humberto Pereira (begini@gmail.com)
#	Siegfried-A. Gevatter (siegfried@gevatter.com)
#	Pedro Assis (pedroh2306@gmail.com)
#	Wim Muskee (wimmuskee@gmail.com)
#	Radics Geza (radicsge@gmail.com)
#
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

"""Wikipedia Extractor:
Extracts and cleans text from Wikipedia database dump and stores output in a
number of files of similar size in a given directory.
Each file contains several documents in the format:

	<doc id="" url="" title="">
        ...
        </doc>

This version performs template expansion by preprocesssng the whole dump and
extracting template definitions.
"""

import sys, os.path
import re, random
import argparse
from itertools import izip
import logging, traceback
import urllib
import bz2, gzip
import codecs
from htmlentitydefs import name2codepoint
import Queue, threading, multiprocessing

### PARAMS ####################################################################

# This is obtained from <siteinfo>
prefix = None

##
# Defined in <siteinfo>
# We include as default Template, when loading external template file.
knownNamespaces = set(['Template'])

##
# Whether to preserve links in output
#
keepLinks = False

##
# Whether to transform sections into HTML
#
keepSections = False

##
# The namespace used for template definitions
templateNamespace = 'Template'

##
# Recognize only these namespaces
# w: Internal links to the Wikipedia
# wiktionary: Wiki dictionary
# wikt: shortcut for Wiktionary
#
acceptedNamespaces = set(['w', 'wiktionary', 'wikt'])

##
# Drop these elements from article text
#
discardElements = set([
        'gallery', 'timeline', 'noinclude', 'pre',
        'table', 'tr', 'td', 'th', 'caption',
        'form', 'input', 'select', 'option', 'textarea',
        'ul', 'li', 'ol', 'dl', 'dt', 'dd', 'menu', 'dir',
        'ref', 'references', 'img', 'imagemap', 'source'
        ])

#=========================================================================
#
# MediaWiki Markup Grammar
 
# Template = "{{" [ "msg:" | "msgnw:" ] PageName { "|" [ ParameterName "=" AnyText | AnyText ] } "}}" ;
# Extension = "<" ? extension ? ">" AnyText "</" ? extension ? ">" ;
# NoWiki = "<nowiki />" | "<nowiki>" ( InlineText | BlockText ) "</nowiki>" ;
# Parameter = "{{{" ParameterName { Parameter } [ "|" { AnyText | Parameter } ] "}}}" ;
# Comment = "<!--" InlineText "-->" | "<!--" BlockText "//-->" ;
#
# ParameterName = ? uppercase, lowercase, numbers, no spaces, some special chars ? ;
#
#=========================================================================== 

# Program version
version = '2.8'

##### Main function ###########################################################

def extract(id, title, page, out):
    """
    :param page: a list of lines.
    """
    text = '\n'.join(page)
    url = get_url(prefix, id)
    header = '<doc id="%s" url="%s" title="%s">\n' % (id, url, title)
    # Separate header from text with a newline.
    header += title + '\n'
    header = header.encode('utf-8')
    text = clean(text)
    footer = "\n</doc>"
    out.reserve(len(header) + len(text) + len(footer))
    print >> out, header
    for line in compact(text):
        print >> out, line.encode('utf-8')
    print >> out, footer

def get_url(prefix, id):
    return "%s?curid=%s" % (prefix, id)

#------------------------------------------------------------------------------

selfClosingTags = [ 'br', 'hr', 'nobr', 'ref', 'references' ]

# These tags are dropped, keeping their content.
# handle 'a' separately, depending on keepLinks
ignoredTags = [
        'b', 'big', 'blockquote', 'center', 'cite', 'div', 'em',
        'font', 'h1', 'h2', 'h3', 'h4', 'hiero', 'i', 'kbd', 'nowiki',
        'p', 'plaintext', 's', 'small', 'span', 'strike', 'strong',
        'sub', 'sup', 'tt', 'u', 'var'
]

placeholder_tags = {'math':'formula', 'code':'codice'}

def normalizeTitle(title):
    """Normalize title"""
    # remove leading/trailing whitespace and underscores
    title = title.strip(' _')
    # replace sequences of whitespace and underscore chars with a single space
    title = re.sub(r'[\s_]+', ' ', title)

    m = re.match(r'([^:]*):(\s*)(\S(?:.*))', title)
    if m:
        prefix = m.group(1)
        if m.group(2):
            optionalWhitespace = ' '
        else:
            optionalWhitespace = ''
        rest = m.group(3)

        ns = normalizeNamespace(prefix)
        if ns in knownNamespaces:
            # If the prefix designates a known namespace, then it might be
            # followed by optional whitespace that should be removed to get
            # the canonical page name
            # (e.g., "Category:  Births" should become "Category:Births").
            title = ns + ":" + ucfirst(rest)
        else:
            # No namespace, just capitalize first letter.
            # If the part before the colon is not a known namespace, then we
            # must not remove the space after the colon (if any), e.g.,
            # "3001: The_Final_Odyssey" != "3001:The_Final_Odyssey".
            # However, to get the canonical page name we must contract multiple
            # spaces into one, because
            # "3001:   The_Final_Odyssey" != "3001: The_Final_Odyssey".
            title = ucfirst(prefix) + ":" + optionalWhitespace + ucfirst(rest)
    else:
        # no namespace, just capitalize first letter
        title = ucfirst(title)
    return title

##
# Removes HTML or XML character references and entities from a text string.
#
# @param text The HTML (or XML) source text.
# @return The plain text, as a Unicode string, if necessary.

def unescape(text):
    def fixup(m):
        text = m.group(0)
        code = m.group(1)
        try:
            if text[1] == "#":  # character reference
                if text[2] == "x":
                    return unichr(int(code[1:], 16))
                else:
                    return unichr(int(code))
            else:               # named entity
                return unichr(name2codepoint[code])
        except:
            return text # leave as is

    return re.sub("&#?(\w+);", fixup, text)

# Match HTML comments
# The buggy template {{Template:T}} has a comment terminating with just "->"
comment = re.compile(r'<!--.*?-->', re.DOTALL)

# Match elements to ignore
discard_element_patterns = []
for tag in discardElements:
    pattern = re.compile(r'<\s*%s\b[^>]*>.*?<\s*/\s*%s>' % (tag, tag), re.DOTALL | re.IGNORECASE)
    discard_element_patterns.append(pattern)

# Match ignored tags
ignored_tag_patterns = []
def ignoreTag(tag):
    left = re.compile(r'<%s\b[^>/]*>' % tag, re.IGNORECASE) # both <ref> and <reference>
    right = re.compile(r'</\s*%s>' % tag, re.IGNORECASE)
    ignored_tag_patterns.append((left, right))

for tag in ignoredTags:
    ignoreTag(tag)

# Match selfClosing HTML tags
selfClosing_tag_patterns = []
for tag in selfClosingTags:
    pattern = re.compile(r'<\s*%s\b[^/]*/\s*>' % tag, re.DOTALL | re.IGNORECASE)
    selfClosing_tag_patterns.append(pattern)

# Match HTML placeholder tags
placeholder_tag_patterns = []
for tag, repl in placeholder_tags.items():
    pattern = re.compile(r'<\s*%s(\s*| [^>]+?)>.*?<\s*/\s*%s\s*>' % (tag, tag), re.DOTALL | re.IGNORECASE)
    placeholder_tag_patterns.append((pattern, repl))

# Match preformatted lines
preformatted = re.compile(r'^ .*?$', re.MULTILINE)

# Match external links (space separates second optional parameter)
externalLink = re.compile(r'\[\w+[^ ]*? (.*?)]')
externalLinkNoAnchor = re.compile(r'\[\w+[&\]]*\]')

# Matches bold/italic
bold_italic = re.compile(r"'''''([^']*?)'''''")
bold = re.compile(r"'''([^']*?)'''")
italic_quote = re.compile(r"''\"([^\"]*?)\"''")
italic = re.compile(r"''([^']*)''")
quote_quote = re.compile(r'""([^"]*?)""')

# Matches space
spaces = re.compile(r' {2,}')

# Matches dots
dots = re.compile(r'\.{4,}')

#----------------------------------------------------------------------
# Expand templates

maxTemplateRecursionLevels = 16
maxParameterRecursionLevels = 10

# check for template beginning
reOpen = re.compile('(?<!{){{(?!{)', re.DOTALL)

def expandTemplates(text, depth=0):
    """
    :param frame: contains pairs (title, args) of previous invocations.
    Template definitions can span several lines.
    :param depth: recursion level.

    Templates are frequently nested. Occasionally, parsing mistakes may cause
    template insertion to enter an infinite loop, for instance when trying to
    instantiate Template:Country

    {{country_{{{1}}}|{{{2}}}|{{{2}}}|size={{{size|}}}|name={{{name|}}}}}

    which is repeatedly trying to insert template 'country_', which is again
    resolved to Template:Country. The straightforward solution of keeping
    track of templates that were already inserted for the current article
    would not work, because the same template may legally be used more than
    once, with different parameters in different parts of the article.
    Therefore, we limit the number of iterations of nested template inclusion.
    """

    # template        = "{{" parts "}}"

    for l in xrange(maxTemplateRecursionLevels):
        res = ''
        cur = 0
        # look for matching {{...}}
        for s,e in findMatchingBraces(text, '{{', 2):
            res += text[cur:s]
            res += expandTemplate(text[s+2:e-2], depth+l)
            cur = e

        if cur == 0:
            return text
        # leftover
        res += text[cur:]
        text = res

    logging.warn('Reached max template recursion: '
                 + str(maxTemplateRecursionLevels))
    return text

# ----------------------------------------------------------------------
# parameter handling

def splitParameters(paramsList, sep='|'):
    """
    Split template parameters at the separator :param sep:, which defaults to
    "|". The fuction can be used also to split also key-value pairs at the
    separator "=".

    Template parameters often contain URLs, internal links, text or even
    template expressions, since we evaluate templates outside in.
    This is required for cases like:
      {{#if: {{{1}}} | {{lc:{{{1}}} | "parameter missing"}}
    Parameters are separated by "|" symbols. However, we
    cannot simply split the string on "|" symbols, since these
    also appear inside templates and internal links, e.g.

     {{if:|
      |{{#if:the president|
           |{{#if:|
               [[Category:Hatnote templates|A{{PAGENAME}}]]
            }}
       }}
     }}

    We split parameters at the "|" symbols that are not inside any pair
    {{{...}}}, {{...}}, [[...]], {|...|}.
    """

    parameters = []
    cur = 0
    for s,e in findBalanced(paramsList,
                            ['{{{', '{{', '[[', '{|'],
                            ['}}}', '}}', ']]', '|}']):
        par = paramsList[cur:s].split(sep)
        if par:
            if parameters:
                # portion before | belongs to previous parameter
                parameters[-1] += par[0]
                if len(par) > 1:
                    # rest are new parameters
                    parameters.extend(par[1:])
            else:
                parameters = par
        elif not parameters:
            parameters = ['']   # create first param
        # add span to last previous parameter
        parameters[-1] += paramsList[s:e]
        cur = e
    # leftover
    par = paramsList[cur:].split(sep)
    if par:
        if parameters:
            # portion before | belongs to previous parameter
            parameters[-1] += par[0]
            if len(par) > 1:
                # rest are new parameters
                parameters.extend(par[1:])
        else:
            parameters = par

    return parameters

def templateParams(parameters, frame):
    """
    Build a dictionary with positional or name key to expanded parameters.
    :param parameters: the parts[1:] of a template, i.e. all except the title.
    """
    templateParams = {}

    if not parameters:
        return templateParams

    # evaluate parameters, since they may contain templates, including the
    # symbol "=".
    # {{#ifexpr: {{{1}}} = 1 }}
    parameters = [expandTemplates(p, frame) for p in parameters]

    # Parameters can be either named or unnamed. In the latter case, their
    # name is defined by their ordinal position (1, 2, 3, ...).

    unnamedParameterCounter = 0

    # It's legal for unnamed parameters to be skipped, in which case they
    # will get default values (if available) during actual instantiation.
    # That is {{template_name|a||c}} means parameter 1 gets
    # the value 'a', parameter 2 value is not defined, and parameter 3 gets
    # the value 'c'.  This case is correctly handled by function 'split',
    # and does not require any special handling.
    for param in parameters:
        # Spaces before or after a parameter value are normally ignored,
        # UNLESS the parameter contains a link (to prevent possible gluing
        # the link to the following text after template substitution)

        # Parameter values may contain "=" symbols, hence the parameter
        # name extends up to the first such symbol.

        # It is legal for a parameter to be specified several times, in
        # which case the last assignment takes precedence. Example:
        # "{{t|a|b|c|2=B}}" is equivalent to "{{t|a|B|c}}".
        # Therefore, we don't check if the parameter has been assigned a
        # value before, because anyway the last assignment should override
        # any previous ones.
        # Don't use DOTALL here since parameters may be tags with
        # attributes, e.g. <div class="templatequotecite">

        m = re.match('([^=]*)=(.*)$', param)
        if m:
            # This is a named parameter.  This case also handles parameter
            # assignments like "2=xxx", where the number of an unnamed
            # parameter ("2") is specified explicitly - this is handled
            # transparently.

            parameterName = m.group(1)
            parameterValue = m.group(2)
          
            parameterName = parameterName.strip()
            if ']]' not in parameterValue: # if the value does not contain a link, trim whitespace
                parameterValue = parameterValue.strip()
            templateParams[parameterName] = parameterValue
        else:
            # this is an unnamed parameter
            unnamedParameterCounter += 1

            if ']]' not in param: # if the value does not contain a link, trim whitespace
                param = param.strip()
            templateParams[str(unnamedParameterCounter)] = param
    return templateParams

def findMatchingBraces(text, openDelim, ldelim):
    """
    :param openDelim: RE matching opening delimiter.
    :param ldelim: number of braces in openDelim.
    """
    # Parsing is done with respect to pairs of double braces {{..}} delimiting
    # a template, and pairs of triple braces {{{..}}} delimiting a tplarg. If
    # double opening braces are followed by triple closing braces or
    # conversely, this is taken as delimiting a template, with one left-over
    # brace outside it, taken as plain text. For any pattern of braces this
    # defines a set of templates and tplargs such that any two are either
    # separate or nested (not overlapping).

    # Unmatched double rectangular closing brackets can be in a template or
    # tplarg, but unmatched double rectangular opening brackets
    # cannot. Unmatched double or triple closing braces inside a pair of
    # double rectangular brackets are treated as plain text.
    # Other formulation: in ambiguity between template or tplarg on one hand,
    # and a link on the other hand, the structure with the rightmost opening
    # takes precedence, even if this is the opening of a link without any
    # closing, so not producing an actual link.

    # In the case of more than three opening braces the last three are assumed
    # to belong to a tplarg, unless there is no matching triple of closing
    # braces, in which case the last two opening braces are are assumed to
    # belong to a template.

    reOpen = re.compile(openDelim)
    cur = 0
    # scan text after {{ (openDelim) looking for matching }}
    while True:
        m = reOpen.search(text, cur)
        if m:
            npar = ldelim
            for i in xrange(m.end(), len(text)):
                if text[i] == '{':
                    npar += 1
                elif text[i] == '}':
                    npar -= 1
                    if npar == 0:
                        yield m.start(), i+1
                        cur = i+1
                        break
            else:
                # unbalanced
                return
        else:
            return

def findBalanced(text, openDelim, closeDelim, openPatterns=None,
                 startDelim=None):
    """
    Assuming that text contains a properly balanced expression using
    :param openDelim: as opening delimiters and
    :param closeDelim: as closing delimiters.
    :param openPatterns: use these regex patterns for matching open delimiters.
      Sometimes patterns are ambiguous, hence specifying '{{{(?!{)' avoids
      matching '{{{{' for '{{{'.
    :param startDelim: start searching for this delimiter.
    :return: an iterator producing pairs (start, end) of start and end
    positions in text containing a balanced expression.
    """
    if openPatterns:
        openPat = '|'.join(openPatterns)
    else:
        openPat = '|'.join([re.escape(x) for x in openDelim])
    # patter for delimiters expected after each opening delimiter
    afterPat = { o:re.compile(openPat+'|'+c, re.DOTALL) for o,c in izip(openDelim, closeDelim)} 
    stack = []
    start = 0
    cur = 0
    end = len(text)
    startSet = False
    if startDelim is not None:
        if openPatterns:
            startPat = re.compile(openPatterns[startDelim])
        else:
            startPat = re.compile(openDelim[startDelim])
    else:
        startPat = re.compile(openPat)
    nextPat = startPat
    while True:
        next = nextPat.search(text, cur)
        if not next:
            return
        if not startSet:
            start = next.start()
            startSet = True
        delim = next.group(0)
        if delim in openDelim:
            stack.append(delim)
            nextPat = afterPat[delim]
        else:
            opening = stack.pop()
            # assert opening == openDelim[closeDelim.index(next.group(0))]
            if stack:
                nextPat = afterPat[stack[-1]]
            else:
                yield start, next.end()
                nextPat = startPat
                start = next.end()
                startSet = False
        cur = next.end()

# ----------------------------------------------------------------------
# Modules

# Only minimal support
# FIXME: import Lua modules.

modules = {
    'convert' : {
        'convert': lambda x, u, *rest: x+' '+u, # no conversion
    }
}

# ----------------------------------------------------------------------
# variables

# FIXME: we just discard them.
magicWords = set([
    '!',
    'currentmonth',
    'currentmonth1',
    'currentmonthname',
    'currentmonthnamegen',
    'currentmonthabbrev',
    'currentday',
    'currentday2',
    'currentdayname',
    'currentyear',
    'currenttime',
    'currenthour',
    'localmonth',
    'localmonth1',
    'localmonthname',
    'localmonthnamegen',
    'localmonthabbrev',
    'localday',
    'localday2',
    'localdayname',
    'localyear',
    'localtime',
    'localhour',
    'numberofarticles',
    'numberoffiles',
    'numberofedits',
    'articlepath',
    'pageid',
    'sitename',
    'server',
    'servername',
    'scriptpath',
    'stylepath',
    'pagename',
    'pagenamee',
    'fullpagename',
    'fullpagenamee',
    'namespace',
    'namespacee',
    'namespacenumber',
    'currentweek',
    'currentdow',
    'localweek',
    'localdow',
    'revisionid',
    'revisionday',
    'revisionday2',
    'revisionmonth',
    'revisionmonth1',
    'revisionyear',
    'revisiontimestamp',
    'revisionuser',
    'revisionsize',
    'subpagename',
    'subpagenamee',
    'talkspace',
    'talkspacee',
    'subjectspace',
    'subjectspacee',
    'talkpagename',
    'talkpagenamee',
    'subjectpagename',
    'subjectpagenamee',
    'numberofusers',
    'numberofactiveusers',
    'numberofpages',
    'currentversion',
    'rootpagename',
    'rootpagenamee',
    'basepagename',
    'basepagenamee',
    'currenttimestamp',
    'localtimestamp',
    'directionmark',
    'contentlanguage',
    'numberofadmins',
    'cascadingsources',
])

# ----------------------------------------------------------------------

substWords = 'subst:|safesubst:'

def expandTemplate(templateInvocation, depth):
    """
    Expands template invocation.
    :param templateInvocation: the parts of a template.
    :param depth: recursion depth.

    :see http://meta.wikimedia.org/wiki/Help:Expansion for an explanation of
    the process.

    See in particular: Expansion of names and values
    http://meta.wikimedia.org/wiki/Help:Expansion#Expansion_of_names_and_values

    For most parser functions all names and values are expanded, regardless of
    what is relevant for the result. The branching functions (#if, #ifeq,
    #iferror, #ifexist, #ifexpr, #switch) are exceptions.

    All names in a template call are expanded, and the titles of the tplargs
    in the template body, after which it is determined which values must be
    expanded, and for which tplargs in the template body the first part
    (default).

    In the case of a tplarg, any parts beyond the first are never expanded.
    The possible name and the value of the first part is expanded if the title
    does not match a name in the template call.

    :see code for braceSubstitution at
    https://doc.wikimedia.org/mediawiki-core/master/php/html/Parser_8php_source.html#3397:

    """

    # Templates and tplargs are decomposed in the same way, with pipes as
    # separator, even though eventually any parts in a tplarg after the first
    # (the parameter default) are ignored, and an equals sign in the first
    # part is treated as plain text.
    # Pipes inside inner templates and tplargs, or inside double rectangular
    # brackets within the template or tplargs are not taken into account in
    # this decomposition.
    # The first part is called title, the other parts are simply called parts.

    # If a part has one or more equals signs in it, the first equals sign
    # determines the division into name = value. Equals signs inside inner
    # templates and tplargs, or inside double rectangular brackets within the
    # part are not taken into account in this decomposition. Parts without
    # equals sign are indexed 1, 2, .., given as attribute in the <name> tag.

    logging.debug('INVOCATION ' + templateInvocation)

    if depth > maxTemplateRecursionLevels:
        return ''

    parts = splitParameters(templateInvocation)
    # part1 is the portion before the first |
    part1 = expandTemplates(parts[0].strip(), depth + 1)

    # SUBST
    if re.match(substWords, part1):
        if part1.startswith('subst'):
            return templateInvocation
        part1 = re.sub(substWords, '', part1)

    if part1.lower() in magicWords:
        if part1 == '!':
            return '|'
        return ''               # FIXME: get variable value

    # Parser functions
    # The first argument is everything after the first colon.
    colon = part1.find(':')
    if colon > 1:
        funct = part1[:colon]
        parts[0] = part1[colon+1:].strip() # side-effect (parts[0] not used later)
        ret = callParserFunction(funct, parts)
        if ret is not None:
            return ret

    title = fullyQualifiedTemplateTitle(part1)

    redirected = redirects.get(title)
    if redirected:
        title = redirected

    if title in templates:
        # Perform parameter substitution

        template = templates[title]
        logging.debug('TEMPLATE ' + template)

        # tplarg          = "{{{" parts "}}}"
        # parts           = [ title *( "|" part ) ]
        # part            = ( part-name "=" part-value ) / ( part-value )
        # part-name       = wikitext-L3
        # part-value      = wikitext-L3
        # wikitext-L3     = literal / template / tplarg / link / comment / 
        #                   line-eating-comment / unclosed-comment /
        #		    xmlish-element / *wikitext-L3

        # A tplarg may contain other parameters as well as templates, e.g.:
        #  {{{text|{{{quote|{{{1|{{error|Error: No text given}}}}}}}}}}}
        # hence no simple RE like this would work:
        # '{{{((?:(?!{{{).)*?)}}}'
        # We must use full CF parsing.

        # the parameter name itself might be computed, e.g.:
        # {{{appointe{{#if:{{{appointer14|}}}|r|d}}14|}}}

        # Because of the multiple uses of double-brace and triple-brace
        # syntax, expressions can sometimes be ambiguous.
        # Precedence rules specifed here:
        # http://www.mediawiki.org/wiki/Preprocessor_ABNF#Ideal_precedence
        # resolve ambiguities like this:
        # {{{{ }}}} -> { {{{ }}} }
        # {{{{{ }}}}} -> {{ {{{ }}} }}
        # 
        # :see: https://en.wikipedia.org/wiki/Help:Template#Handling_parameters

        # build a dict of name-values for the expanded parameters
        params = templateParams(parts[1:], depth)

        # We perform substitution iteratively.
        # We also limit the maximum number of iterations to avoid too long or
        # even endless loops (in case of malformed input).

        # :see: http://meta.wikimedia.org/wiki/Help:Expansion#Distinction_between_variables.2C_parser_functions.2C_and_templates
        #
        # Parameter values are assigned to parameters in two (?) passes.
        # Therefore a parameter name in a template can depend on the value of
        # another parameter of the same template, regardless of the order in
        # which they are specified in the template call, for example, using
        # Template:ppp containing "{{{{{{p}}}}}}", {{ppp|p=q|q=r}} and even
        # {{ppp|q=r|p=q}} gives r, but using Template:tvvv containing
        # "{{{{{{{{{p}}}}}}}}}", {{tvvv|p=q|q=r|r=s}} gives s.

        for i in xrange(maxParameterRecursionLevels):
            result = ''
            start = 0
            n = 0               # no. of matches
            # we must include '{{' in search or else
            # {{{1|{{PAGENAME}}} would match
            # we must handle 5 {'s as in:
            # {{#if:{{{{{#if:{{{nominee|}}}|nominee|candidate}}|}}}|
            for s,e in findBalanced(template, ['{{{', '{{'], ['}}}', '}}'],
                                    ['(?<!{){{{', '{{'], 0):
                result += template[start:s] + substParameter(template[s+3:e-3],
                                                             params, i)
                start = e
                n += 1
            if n == 0:          # no match
                break
            result += template[start:]                     # leftover
            template = result
        else:
            logging.warn('Reachead maximum parameter recursions: '
                         + str(maxParameterRecursionLevels))
        if depth < maxTemplateRecursionLevels:
            logging.debug('instantiated ' + str(depth) + ' ' + template)
            ret = expandTemplates(template, depth + 1)
            return ret
        else:
            logging.warn('Reached max template recursion: '
                         + str(maxTemplateRecursionLevels))
            return template

    else:
        # The page being included could not be identified
        return ""

def substParameter(parameter, templateParams, depth):
    """
    :param parameter: the parts of a tplarg.
    :param templateParams: dict of name-values template parameters.
    """

    # the parameter name itself might contain templates, e.g.:
    # appointe{{#if:{{{appointer14|}}}|r|d}}14|

    if '{{{' in parameter:
        subst = ''
        start = 0
        for s,e in findMatchingBraces(parameter, '(?<!{){{{(?!{)', 3):
            subst += parameter[start:s] + substParameter(parameter[s+3:e-3],
                                                         templateParams,
                                                         depth + 1)
            start = e
        parameter = subst + parameter[start:]

    if '{{' in parameter:
        parameter = expandTemplates(parameter, depth + 1)

    # any parts in a tplarg after the first (the parameter default) are
    # ignored, and an equals sign in the first part is treated as plain text.

    m = re.match('([^|]*)\|([^|]*)', parameter, flags=re.DOTALL)
    if m:
        # This parameter has a default value
        paramName = m.group(1)
        defaultValue = m.group(2)

        if paramName in templateParams:
            return templateParams[paramName]  # use parameter value specified in template invocation
        else: # use the default value
            return defaultValue
    # parameter without a default value
    elif parameter in templateParams:
        return templateParams[parameter]  # use parameter value specified in template invocation
    else:
        # Parameter not specified in template invocation and does not
        # have a default value.
        # The Wiki rules for templates
        # (see http://meta.wikimedia.org/wiki/Help:Template)
        # would require to keep the parameter in 3 braces, but in our
        # case we drop them.
        return ''
    # Surplus parameters - i.e., those assigned values in template
    # invocation but not used in the template body - are simply ignored.

def ucfirst(string):
    """:return: a string with its first character uppercase"""
    if string:
        if len(string) > 1:
            return string[0].upper() + string[1:]
        else:
            return string.upper()
    else:
        return ''

def lcfirst(string):
    """:return: a string with its first character lowercase"""
    if string:
        if len(string) > 1:
            return string[0].lower() + string[1:]
        else:
            return string.lower()
    else:
        return ''

def fullyQualifiedTemplateTitle(templateTitle):
    """
    Determine the namespace of the page being included through the template
    mechanism
    """
    if templateTitle.startswith(':'):
        # Leading colon by itself implies main namespace, so strip this colon
        return ucfirst(templateTitle[1:])
    else:
        m = re.match('([^:]*)(:.*)', templateTitle)
        if m:
            # colon found but not in the first position - check if it
            # designates a known namespace
            prefix = normalizeNamespace(m.group(1))
            if prefix in knownNamespaces:
                return prefix + ucfirst(m.group(2))
    # The title of the page being included is NOT in the main namespace and
    # lacks any other explicit designation of the namespace - therefore, it
    # is resolved to the Template namespace (that's the default for the
    # template inclusion mechanism).

    # This is a defense against pages whose title only contains UTF-8 chars
    # that are reduced to an empty string. Right now I can think of one such
    # case - <C2><A0> which represents the non-breaking space.
    # In this particular case, this page is a redirect to [[Non-nreaking
    # space]], but having in the system a redirect page with an empty title
    # causes numerous problems, so we'll live happier without it.
    if templateTitle:
        return "Template:" + ucfirst(templateTitle)
    else:
        logging.warn("Skipping page with empty title")
        return ''

def normalizeNamespace(ns):
    return ucfirst(ns)

# ----------------------------------------------------------------------
# see http://www.mediawiki.org/wiki/Help:Extension:ParserFunctions
# https://github.com/Wikia/app/blob/dev/extensions/ParserFunctions/ParserFunctions_body.php

def sharp_expr(expr):
    try:
        expr = re.sub('mod', '%', expr)
        return str(eval(expr))
    except:
        return ""

def sharp_if(testValue, valueIfTrue, valueIfFalse=None, *args):
    if testValue.strip():
        # The {{#if:}} function is an if-then-else construct.
        # The applied condition is: "The condition string is non-empty". 
        valueIfTrue = valueIfTrue.strip()
        if valueIfTrue:
            return valueIfTrue
    elif valueIfFalse:
        return valueIfFalse.strip()
    return ""

def sharp_ifeq(lvalue, rvalue, valueIfTrue, valueIfFalse=None, *args):
    rvalue = rvalue.strip()
    if rvalue:
        # lvalue is always defined
        if lvalue.strip() == rvalue:
            # The {{#ifeq:}} function is an if-then-else construct. The
            # applied condition is "is rvalue equal to lvalue". Note that this
            # does only string comparison while MediaWiki implementation also
            # supports numerical comparissons.

            if valueIfTrue:
                return valueIfTrue.strip()
        else:
            if valueIfFalse:
                return valueIfFalse.strip()
    return ""

def sharp_iferror(test, then='', Else=None, *args):
    if re.match('<(?:strong|span|p|div)\s(?:[^\s>]*\s+)*?class="(?:[^"\s>]*\s+)*?error(?:\s[^">]*)?"', test):
        return then
    elif Else is None:
        return test.strip()
    else:
        return Else.strip()

def sharp_switch(primary, *templateParams):
    # FIXME: we don't support numeric expressions in primary

    # {{#switch: comparison string
    #  | case1 = result1
    #  | case2 
    #  | case4 = result2
    #  | #default = result3
    # }}

    primary = primary.strip()
    found = False
    default = None
    rvalue = None
    lvalue = ''
    for param in templateParams:
        pair = splitParameters(param, '=')
        lvalue = pair[0].strip()
        rvalue = None
        if len(pair) > 1:
            # got "="
            rvalue = pair[1].strip()
            if found or lvalue == primary:
                # Found a match, return now
                return rvalue.strip()
            elif lvalue.startswith('#default'):
                default = rvalue
                # else wrong case, continue
        elif lvalue == primary:
            # If the value matches, set a flag and continue
            found = True
    # Default case
    # Check if the last item had no = sign, thus specifying the default case
    if not rvalue:
        return lvalue
    elif default:
        return default
    return ''

# Extension Scribuntu
# def sharp_invoke(module, function, frame):
#     functions = modules.get(module)
#     if functions:
#         funct = functions.get(function)
#         if funct:
#             templateTitle = fullyQualifiedTemplateTitle(function)
#             # find parameters in frame whose title is the one of the original
#             # template invocation
#             pair = next((x for x in frame if x[0] == templateTitle), None)
#             if pair:
#                 return funct(*pair[1].values())
#             else:
#                 return funct()
#     return None

parserFunctions = {

    '#expr': sharp_expr,

    '#if': sharp_if,

    '#ifeq': sharp_ifeq,

    '#iferror': sharp_iferror,

    '#ifexpr': lambda *args: '', # not supported

    '#ifexist': lambda *args: '', # not supported

    '#rel2abs': lambda *args: '', # not supported

    '#switch': sharp_switch,

    '#language': lambda *args: '', # not supported

    '#time': lambda *args: '', # not supported

    '#timel': lambda *args: '', # not supported

    '#titleparts': lambda *args: '', # not supported

    # This function is used in some pages to construct links
    # http://meta.wikimedia.org/wiki/Help:URL
    'urlencode': lambda string, *rest: urllib.quote(string.encode('utf-8')),

    'lc': lambda string: string.lower() if string else '',

    'lcfirst': lambda string: lcfirst(string),

    'lc': lambda string: string.upper() if string else '',

    'ucfirst': lambda string: ucfirst(string),

    'int': lambda  string: string,

}

def callParserFunction(functionName, args):
    """
    Parser functions have similar syntax as templates, except that
    the first argument is everything after the first colon.

    http://meta.wikimedia.org/wiki/Help:ParserFunctions
    """
  
    try:
       # if functionName == '#invoke':
       #     # special handling of frame
       #     return sharp_invoke(args[0].strip(), args[1].strip(), frame)
       if functionName in parserFunctions:
           return parserFunctions[functionName](*args)
    except:
        return None             # FIXME: fix errors

    return ""

# ----------------------------------------------------------------------
# Expand using WikiMedia API
# import json

# def expandTemplates(text):
#     """Expand templates invoking MediaWiki API"""
#     text = urlib.urlencodew(text.encode('utf-8'))
#     base = prefix[:prefix.rfind('/')]
#     url = base + "/w/api.php?action=expandtemplates&format=json&text=" + text
#     exp = json.loads(urllib.urlopen(url))
#     return exp['expandtemplates']['*']

# ----------------------------------------------------------------------
# Extract Template definition

reNoinclude = re.compile(r'<noinclude>(?:.*?)</noinclude>', re.DOTALL)
reIncludeonly = re.compile(r'<includeonly>|</includeonly>', re.DOTALL)

templates = {}
redirects = {}

def define_template(title, page):
    global templates
    global redirects

    #title = normalizeTitle(title)

    # check for redirects
    m = re.match('#REDIRECT.*?\[\[([^\]]*)]]', page[0])
    if m:
        redirects[title] = m.group(1) #normalizeTitle(m.group(1))
        return

    text = unescape(''.join(page))

    # We're storing template text for future inclusion, therefore,
    # remove all <noinclude> text and keep all <includeonly> text
    # (but eliminate <includeonly> tags per se).
    # However, if <onlyinclude> ... </onlyinclude> parts are present,
    # then only keep them and discard the rest of the template body.
    # This is because using <onlyinclude> on a text fragment is
    # equivalent to enclosing it in <includeonly> tags **AND**
    # enclosing all the rest of the template body in <noinclude> tags.

    # remove comments
    text = comment.sub('', text)

    onlyincludeAccumulator = ''
    for m in re.finditer('<onlyinclude>(.*?)</onlyinclude>', text, re.DOTALL):
        onlyincludeAccumulator += m.group(1) + "\n"
    if onlyincludeAccumulator:
        text = onlyincludeAccumulator
    else:
        # If there are no <onlyinclude> fragments, simply eliminate
        # <noinclude> fragments and keep <includeonly> ones.
        text = reNoinclude.sub('', text)
        # eliminate unterminated <noinclude> elements
        text = re.sub(r'<noinclude\s*>.*$', '', text, flags=re.DOTALL)

        text = reIncludeonly.sub('', text)

    if text:
        if title in templates:
            logging.warn('Redefining: ' + title)
        templates[title] = text

# ----------------------------------------------------------------------

def dropNested(text, openDelim, closeDelim):
    """
    A matching function for nested expressions, e.g. namespaces and tables.
    """
    openRE = re.compile(openDelim)
    closeRE = re.compile(closeDelim)
    # partition text in separate blocks { } { }
    spans = []                # pairs (s, e) for each partition
    nest = 0                    # nesting level
    start = openRE.search(text, 0)
    if not start:
        return text
    end = closeRE.search(text, start.end())
    next = start
    while end:
        next = openRE.search(text, next.end())
        if not next:            # termination
            while nest:         # close all pending
                nest -=1
                end0 = closeRE.search(text, end.end())
                if end0:
                    end = end0
                else:
                    break
            spans.append((start.start(), end.end()))
            break
        while end.end() < next.start():
            # { } {
            if nest:
                nest -= 1
                # try closing more
                last = end.end()
                end = closeRE.search(text, end.end())
                if not end:     # unbalanced
                    if spans:
                        span = (spans[0][0], last)
                    else:
                        span = (start.start(), last)
                    spans = [span]
                    break
            else:
                spans.append((start.start(), end.end()))
                # advance start, find next close
                start = next
                end = closeRE.search(text, next.end())
                break           # { }
        if next != start:
            # { { }
            nest += 1
    # collect text outside partitions
    return dropSpans(spans, text)

def dropSpans(spans, text):
    """
    Drop from text the blocks identified in :param spans:, possibly nested.
    """
    spans.sort()
    res = ''
    offset = 0
    for s, e in  spans:
        if offset <= s:         # handle nesting
            if offset < s:
                res += text[offset:s]
            offset = e
    res += text[offset:]
    return res

# Match interwiki links, | separates parameters.
# First parameter is displayed, also trailing concatenated text included
# in display, e.g. s for plural).
#
# Can be nested [[File:..|..[[..]]..|..]], [[Category:...]], etc.
# We first expand inner ones, than remove enclosing ones.
#
wikiLink = re.compile(r'\[\[([^[]*?)(?:\|([^[]*?))?\]\](\w*)')

parametrizedLink = re.compile(r'\[\[[^\]]*?\]\]')

# Function applied to wikiLinks
def make_anchor_tag(match):
    global keepLinks
    link = match.group(1)
    colon = link.find(':')
    if colon > 0 and link[:colon] not in acceptedNamespaces:
        return ''
    trail = match.group(3)
    anchor = match.group(2)
    if not anchor:
        anchor = link
    anchor += trail
    if keepLinks:
        return '<a href="%s">%s</a>' % (link, anchor)
    else:
        return anchor

# ----------------------------------------------------------------------

def clean(text):

    # expand templates
    # See: http://www.mediawiki.org/wiki/Help:Templates
    text = expandTemplates(text)

    # Drop transclusions (template, parser functions)
    text = dropNested(text, r'{{', r'}}')

    # Drop tables
    text = dropNested(text, r'{\|', r'\|}')

    # Drop preformatted
    # Done after dropping transclusions (since {{Cite ..}} are often indented)
    # but before dropping links, since they might leave a space in front
    # of a line, e.g. "[[File: something]] Rest..." => " Rest..."

    text = preformatted.sub('', text)

    # Expand links
    text = wikiLink.sub(make_anchor_tag, text)
    # Drop all remaining ones
    text = parametrizedLink.sub('', text)

    # Handle external links
    text = externalLink.sub(r'\1', text)
    text = externalLinkNoAnchor.sub('', text)

    # Handle bold/italic/quote
    text = bold_italic.sub(r'\1', text)
    text = bold.sub(r'\1', text)
    text = italic_quote.sub(r'&quot;\1&quot;', text)
    text = italic.sub(r'&quot;\1&quot;', text)
    text = quote_quote.sub(r'\1', text)
    # residuals of unbalanced quotes
    text = text.replace("'''", '').replace("''", '&quot;')

    ################ Process HTML ###############

    # turn into HTML
    text = unescape(text)
    # do it again (&amp;nbsp;)
    text = unescape(text)

    # Collect spans

    spans = []
    # Drop HTML comments
    for m in comment.finditer(text):
            spans.append((m.start(), m.end()))

    # Drop self-closing tags
    for pattern in selfClosing_tag_patterns:
        for m in pattern.finditer(text):
            spans.append((m.start(), m.end()))

    # Drop ignored tags
    for left, right in ignored_tag_patterns:
        for m in left.finditer(text):
            spans.append((m.start(), m.end()))
        for m in right.finditer(text):
            spans.append((m.start(), m.end()))

    # Bulk remove all spans
    text = dropSpans(spans, text)

    # Drop discarded elements
    start = []
    end = []
    for pattern in discard_element_patterns:
        for m in pattern.finditer(text):
            start.append(m.start())
            end.append(m.end())
    # bulk removal
    spans = [p for p in izip(start, end)]
    text = dropSpans(spans, text)

    # Expand placeholders
    for pattern, placeholder in placeholder_tag_patterns:
        index = 1
        for match in pattern.finditer(text):
            text = text.replace(match.group(), '%s_%d' % (placeholder, index))
            index += 1

    text = text.replace('<<', u'«').replace('>>', u'»')

    #############################################

    # Cleanup text
    text = text.replace('\t', ' ')
    text = spaces.sub(' ', text)
    text = dots.sub('...', text)
    text = re.sub(u' (,:\.\)\]»)', r'\1', text)
    text = re.sub(u'(\[\(«) ', r'\1', text)
    text = re.sub(r'\n\W+?\n', '\n', text) # lines with only punctuations
    text = text.replace(',,', ',').replace(',.', '.')
    return text

section = re.compile(r'(==+)\s*(.*?)\s*\1')

def compact(text):
    """Deal with headers, lists, empty sections, residuals of tables"""
    page = []                   # list of paragraph
    headers = {}                # Headers for unfilled sections
    emptySection = False        # empty sections are discarded
    inList = False              # whether opened <UL>

    for line in text.split('\n'):

        if not line:
            continue
        # Handle section titles
        m = section.match(line)
        if m:
            title = m.group(2)
            lev = len(m.group(1))
            if keepSections:
                page.append("<h%d>%s</h%d>" % (lev, title, lev))
            if title and title[-1] not in '!?':
                title += '.'
            headers[lev] = title
            # drop previous headers
            for i in headers.keys():
                if i > lev:
                    del headers[i]
            emptySection = True
            continue
        # Handle page title
        if line.startswith('++'):
            title = line[2:-2]
            if title:
                if title[-1] not in '!?':
                    title += '.'
                page.append(title)
        # handle indents
        elif line[0] == ':':
            page.append(line[1:])
        # handle lists
        elif line[0] in '*#;':
            if keepSections:
                page.append("<li>%s</li>" % line[1:])
            else:
                continue
        # Drop residuals of lists
        elif line[0] in '{|' or line[-1] in '}':
            continue
        # Drop irrelevant lines
        elif (line[0] == '(' and line[-1] == ')') or line.strip('.-') == '':
            continue
        elif len(headers):
            items = headers.items()
            items.sort()
            for (i, v) in items:
                page.append(v)
            headers.clear()
            page.append(line)   # first line
            emptySection = False
        elif not emptySection:
            page.append(line)

    return page

def handle_unicode(entity):
    numeric_code = int(entity[2:-1])
    if numeric_code >= 0x10000: return ''
    return unichr(numeric_code)

#------------------------------------------------------------------------------

class OutputSplitter:
    def __init__(self, path_name=None, max_file_size=0, compress=True):
        self.dir_index = 0
        self.file_index = -1
        self.compress = compress
        self.max_file_size = max_file_size
        self.path_name = path_name
        if path_name:
            self.out_file = self.open_next_file()
        else:
            self.out_file = sys.stdout

    def reserve(self, size):
        if self.path_name:
            cur_file_size = self.out_file.tell()
            if cur_file_size + size > self.max_file_size:
                self.close()
                self.out_file = self.open_next_file()

    def write(self, text):
        self.out_file.write(text)

    def close(self):
        self.out_file.close()

    def open_next_file(self):
        self.file_index += 1
        if self.file_index == 100:
            self.dir_index += 1
            self.file_index = 0
        dir_name = self._dir_name()
        if not os.path.isdir(dir_name):
            os.makedirs(dir_name)
        file_name = os.path.join(dir_name, self._file_name())
        if self.compress:
            return bz2.BZ2File(file_name + '.bz2', 'w')
        else:
            return open(file_name, 'w')

    def _dir_name(self):
        char1 = self.dir_index % 26
        char2 = self.dir_index / 26 % 26
        return os.path.join(self.path_name, '%c%c' % (ord('A') + char2, ord('A') + char1))

    def _file_name(self):
        return 'wiki_%02d' % self.file_index

# ----------------------------------------------------------------------
# READER

tagRE = re.compile(r'(.*?)<(/?\w+)[^>]*>(?:([^<]*)(<.*?>)?)?')
#tagRE = re.compile(r'(.*?)<(/?\w+)[^>]*>([^<]*)')
#                    1     2            3

def load_templates(file, output_file=None):
    """
    Load templates from :param file:.
    :param output_file: file where to save templates.
    """
    templatePrefix = templateNamespace + ':'
    articles = 0
    page = []
    inText = False
    if output_file:
        output = codecs.open(output_file, 'wb', 'utf-8')
    for line in file:
        line = line.decode('utf-8')
        if '<' not in line:         # faster than doing re.search()
            if inText:
                page.append(line)
            continue
        m = tagRE.search(line)
        if not m:
            continue
        tag = m.group(2)
        if tag == 'page':
            page = []
        elif tag == 'title':
            title = m.group(3)
        elif tag == 'text':
            inText = True
            line = line[m.start(3):m.end(3)]
            page.append(line)
            if m.lastindex == 4: # open-close
                inText = False
        elif tag == '/text':
            if m.group(1):
                page.append(m.group(1))
            inText = False
        elif inText:
            page.append(line)
        elif tag == '/page':
            if title.startswith(templatePrefix):
                define_template(title, page)
                if output_file:
                    output.write('<page>\n')
                    output.write('   <title>%s</title>\n' % title)
                    output.write('   <ns>10</ns>\n')
                    output.write('   <text>')
                    for line in page:
                        output.write(line)
                    output.write('   </text>\n')
                    output.write('</page>\n')
            page = []
            articles += 1
            if articles % 10000 == 0:
                logging.info("Preprocessed: %d pages" % articles)

def process_data(input_file, template_file, output):
    """
    :param input_file: name of the wikipedia dump file.
    :param template_file: optional file with template definitions.
    :param output: name of the directory where to store extracted files.
    """
    global prefix
    global knownNamespaces
    global templateNamespace

    # preprocess
    logging.info("Preprocessing dump to collect template definitions: this may take some time.")

    if input_file.lower().endswith("bz2"):
        opener = bz2.BZ2File
    else:
        opener = open

    input = opener(input_file)

    # collect siteinfo
    for line in input:
        line = line.decode('utf-8')
        m = tagRE.search(line)
        if not  m:
            continue
        tag = m.group(2)
        if tag == 'base':
            # discover prefix from the xml dump file
            # /mediawiki/siteinfo/base
            base = m.group(3)
            prefix = base[:base.rfind("/")]
        elif tag == 'namespace':
            knownNamespaces.add(m.group(3))
            if re.search('key="10"', line):
                templateNamespace = m.group(3)
        elif tag == '/siteinfo':
            break

    if template_file and os.path.exists(template_file):
        input.close()
        with open(template_file) as file:
            load_templates(file)
    else:
        load_templates(input, template_file)
        input.close()

    # process pages
    logging.info("Starting processing pages from %s." % input_file)

    input = opener(input_file)

    page = []
    id = None
    inText = False
    redirect = False
    for line in input:
        line = line.decode('utf-8')
        if '<' not in line:         # faster than doing re.search()
            if inText:
                page.append(line)
            continue
        m = tagRE.search(line)
        if not m:
            continue
        tag = m.group(2)
        if tag == 'page':
            page = []
            redirect = False
        elif tag == 'id' and not id:
            id = m.group(3)
        elif tag == 'title':
            title = m.group(3)
        elif tag == 'redirect':
            redirect = True
        elif tag == 'text':
            inText = True
            line = line[m.start(3):m.end(3)]
            page.append(line)
            if m.lastindex == 4: # open-close
                inText = False
        elif tag == '/text':
            if m.group(1):
                page.append(m.group(1))
            inText = False
        elif inText:
            page.append(line)
        elif tag == '/page':
            colon = title.find(':')
            if (colon < 0 or title[:colon] in acceptedNamespaces) and \
                    not redirect and not title.startswith(templateNamespace):
                logging.info("%s\t%s" % (id, title))
                extract(id, title, page, output)
            id = None
            page = []

    input.close()

# ----------------------------------------------------------------------
# Multithread version

class ExtractorThread(threading.Thread):
    
    _filename_lock = threading.RLock()    
    
    def __init__(self, queue, outputdir, maxfilesize, prefix, compress):
        threading.Thread.__init__(self)
        self._queue = queue
        self._maxfilesize = maxfilesize
        self._prefix = prefix
        self._compress = compress
        self._outputdir = outputdir
        if not os.path.exists(outputdir):
            os.mkdir(outputdir)
        self._outfile = None
        
    @classmethod
    def _get_file(cls, outputdir, compress=False):
        with cls._filename_lock:
            fpath = None
            while not fpath or os.path.exists(fpath):
                fname = ''.join([random.choice(string.letters) for _ in range(16)])
                ext = ".txt" if not compress else ".txt.bz2"
                fpath = os.path.join(outputdir, fname + ext)    
                
            if compress:
                return bz2.BZ2File(fpath, 'w')
                
            return open(fpath, 'w')
            
    def _get_url(self, prefix, id):
        return "%s?curid=%s" % (prefix, id)        
    
    def _write(self, id, title, text):
        if not self._outfile:
            self._outfile = self._get_file(self._outputdir, self._compress)
        
        logging.info(("[%s] [%s]" % (id, title)).encode('utf-8'))
        
        url = self._get_url(self._prefix, id)    
        
        header = '<doc id="%s" url="%s" title="%s">%s\n' % (id, url, title, title)
        footer = "\n</doc>"
        self._outfile.write(header.encode("utf-8")) 
        for line in compact(clean(text)):
            self._outfile.write(line.encode("utf-8"))
        self._outfile.write(footer)        
    
    def run(self):
        while True:
            try:
                page = self._queue.get(timeout=1)
                if page:
                    self._write(page)
            except Queue.Empty:
                break
            except:
                logging.error(traceback.format_exc())
            finally:
                self._queue.task_done()
                    
        logging.info("%s done" % self.name)

# ----------------------------------------------------------------------

# Minimum size of output files
minFileSize = 200 * 1024

def main():
    global keepLinks, keepSections, prefix, acceptedNamespaces

    parser = argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]),
        formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=__doc__)
    parser.add_argument("input",
                        help="XML wiki dump file")
    parser.add_argument("-o", "--output", default="text",
                        help="output directory")
    parser.add_argument("-b", "--bytes", default="1M",
                        help="put specified bytes per output file (default is %(default)s)", metavar="n[KM]")
    parser.add_argument("-B", "--base",
                        help="base URL for the Wikipedia pages")
    parser.add_argument("-c", "--compress", action="store_true",
                        help="compress output files using bzip")
    parser.add_argument("-l", "--links", action="store_true",
                        help="preserve links")
    parser.add_argument("-ns", "--namespaces", default="", metavar="ns1,ns2",
                        help="accepted namespaces")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="suppress reporting progress info")
    parser.add_argument("--debug", action="store_true",
                        help="print debug info")
    parser.add_argument("-s", "--sections", action="store_true",
                        help="preserve sections")
    parser.add_argument("-a", "--article", action="store_true",
                        help="analyze a file containing a single article (debug) option")
    # parser.add_argument("-f", "--format", choices=(PLAIN, JSON), default=PLAIN,
    #                     help="choose output format default is %(default)s")
    parser.add_argument("--templates",
                        help="use or create file containing templates")
    parser.add_argument("-v", "--version", action="version",
                        version='%(prog)s ' + version,
                        help="print program version")

    args = parser.parse_args()
    
    keepLinks = args.links
    keepSections = args.sections

    if args.base:
        prefix = args.base

    try:
        if args.bytes[-1] in 'kK':
            file_size = int(args.bytes[:-1]) * 1024
        elif args.bytes[-1] in 'mM':
            file_size = int(args.bytes[:-1]) * 1024 * 1024
        else:
            file_size = int(args.bytes)
        if file_size < minFileSize: raise ValueError()
    except ValueError:
        logging.error('Insufficient or invalid size: %s' % args.bytes)
        return

    if args.namespaces:
        acceptedNamespaces = set(args.ns.split(','))

    logger = logging.getLogger()
    if not args.quiet:
        logger.setLevel(logging.INFO)
    if args.debug:
        logger.setLevel(logging.DEBUG)

    input_file = args.input

    if not keepLinks:
        ignoreTag('a')

    if args.article:
        if args.templates:
            if os.path.exists(args.templates):
                with open(args.templates) as file:
                    load_templates(file)

        with open(input_file) as file:
            page = file.read().decode('utf-8')
            m = re.search(r'<id>(.*)</id>', page)
            if m:
                id = m.group(1)
            m = re.search(r'<title>(.*)</title>', page)
            if m:
                title = m.group(1)
            extract(id, title, [page], OutputSplitter())
        return

    output_dir = args.output
    if not os.path.isdir(output_dir):
        try:
            os.makedirs(output_dir)
        except:
            logging.error('Could not create: %s' % output_dir)
            return

    output_splitter = OutputSplitter(output_dir, file_size, args.compress)
    process_data(input_file, args.templates, output_splitter)
    output_splitter.close()

if __name__ == '__main__':
    main()
