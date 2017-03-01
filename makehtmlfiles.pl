#!/usr/bin/perl

# vystup z wikiextractor ve formatu html rozseka podle tagu 'doc' na jednotlive
# soubory, prida k nim html hlavicku/paticku a upravi odkazy
use strict;
use URI::Escape;
use File::Basename;
use File::Path qw(make_path);
use HTML::Entities;

my ($out_dir) = @ARGV;
if (not defined $out_dir) {
  die "Missing param, usage: makehtmlfiles.pl <output_dir>\n";
}

my $html_head_tmpl = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
  <title>OFFLINE MEDIAWIKI</title>
</head>
<body>';
my $html_head = '';

my $html_foot = "\n</body></html>\n";

my $basedir = '';
my $title = '';
my $suffix = 'html';
my $filename = '';
my $filename_index = "index.$suffix";
my $line = '';
my $FILE;
my $INDEX;
my %index = ();
my $indx = ''; # sorted index
my $relative_path = '';

make_path("$out_dir/pages", 0700) unless(-d "$out_dir/pages" );
make_path("$out_dir/images", 0700) unless(-d "$out_dir/images" );

foreach $line ( <STDIN> ) {
    chomp( $line );
    if ($line =~ /^\s*<doc.*title="(.*?)".*>\s*$/) {
        $title = "$1";
        #$filename = uri_escape("$title") . ".$suffix";
        $filename = "$title" . ".$suffix";
        # print "$title \t-> $filename\n";
        
        $filename =~ s/\s/_/g; 
        $basedir = dirname("$filename");
        # print "MKDIR $basedir\n";
        make_path("$out_dir/pages/$basedir", 0700) unless(-d "$out_dir/pages/$basedir" );        

        open($FILE, ">", "$out_dir/pages/$filename") or die "cannot open > $out_dir/$filename: $!";

        $html_head = $html_head_tmpl;
        $html_head =~ s#<title>OFFLINE MEDIAWIKI</title>#<title>$title</title>#;
        print $FILE "$html_head";
        print $FILE "\n<!-- $line -->\n";
        # insert to index
        $index{"$title"} = uri_escape("$filename");

        # prepare relative path - update URI references
        $relative_path = $basedir;
        $relative_path =~ s#[^/]+#..#g if $relative_path !~ /^\.$/;
        $relative_path .= "/";
        $relative_path = '' if $relative_path =~ m#^./$#;
        # print "$basedir -> $relative_path\n";

        next;
    }

    if ($line =~ /^\s*<\/doc>\s*$/) {
        print $FILE "$html_foot";
        close $FILE;
        next;
    }
   
    # fix URI 
    decode_entities($line);
    $line =~ s#href="(.*?)"#href="$relative_path\1.$suffix"#g;
    $line =~ s/(?<=href=")([^"]*)/($a=$1)=~s, |%20,_,g;"$a"/ge ;
    $line =~ s/(?<=href="http)([^"]*)/($a=$1)=~s,%3A,:,g;"$a"/ge ;

    # fix images
    $line =~ s#img src="(.*?)"#img src="$relative_path../images/\u\1"#g;
    $line =~ s/(?<=img src=")([^"]*)/($a=$1)=~s, |%20,_,g;"$a"/ge ;
    $line =~ s/(?<=img src="http)([^"]*)/($a=$1)=~s,%3A,:,g;"$a"/ge ;

    print $FILE "$line";
}

# make index.html
open($INDEX, ">", "$out_dir/$filename_index") or die "cannot open > $out_dir/$filename_index: $!";
$html_head = $html_head_tmpl;
$html_head =~ s#<title>OFFLINE MEDIAWIKI</title>#<title>Index of MediaWiki dump</title>#;
print $INDEX "$html_head";

foreach $indx (sort keys %index) {
    print $INDEX "<a href=\"pages/$index{$indx}\">$indx</a><br>";
}

print $INDEX "$html_foot";
close $INDEX;

exit 0;

