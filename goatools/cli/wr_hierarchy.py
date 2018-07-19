"""Command-line script to print a GO term's lower-level hierarchy.

Usage:
  wr_hier.py [GO ...] [options]

Options:
  -h --help      show this help message and exit

  -i <gofile.txt>  Read a file name containing a list of GO IDs
  -o <outfile>     Output file in ASCII text format
  -f               Writes results to an ASCII file named after the GO term. e.g. hier_GO0002376.txt
  --up             Write report from GO term up to root

  --dag=<dag_file>    Ontologies in obo file [default: go-basic.obo].

  --gaf=<file.gaf>    Annotations from a gaf file
  --gene2go=<gene2go> Annotations from a gene2go file downloaded from NCBI
  --taxid=<Taxonomy_number> Taxid is required is using gene2go

  --no_indent         Do not indent GO terms
  --max_indent=<int>  max indent depth for printing relative to GO Term
  --concise           If a branch has already been printed, do not re-print.
                      Print '===' instead of dashes to note the point of compression
  --dash_len=<int>    Printed width of the dashes column [default: 6]
  --go_marks=<GOs>    GO IDs to be marked
  -r --relationship   Load and use the 'relationship' field
"""

from __future__ import print_function

__copyright__ = "Copyright (C) 2016-2018, DV Klopfenstein, H Tang. All rights reserved."
__author__ = "DV Klopfenstein"

import os
import sys
from goatools.base import get_godag
from goatools.associations import read_annotations
from goatools.associations import get_b2aset
from goatools.semantic import TermCounts
from goatools.godag.obo_optional_attributes import OboOptionalAttrs
from goatools.cli.docopt_parse import DocOptParse
from goatools.cli.gos_get import GetGOs
from goatools.gosubdag.gosubdag import GoSubDag
from goatools.gosubdag.rpt.write_hierarchy import WrHierGO


def cli():
    """Command-line script to print a GO term's lower-level hierarchy."""
    objcli = WrHierCli(sys.argv[1:])
    fouts_txt = objcli.get_fouts()
    if fouts_txt:
        for fout_txt in fouts_txt:
            objcli.wrtxt_hier(fout_txt)
    else:
        objcli.prt_hier(sys.stdout)


class WrHierCli(object):
    """Write hierarchy cli."""

    kws_set_all = set(['relationship', 'up', 'f'])
    kws_dct_all = set(['GO', 'dag', 'i', 'o', 'max_indent', 'no_indent', 'concise',
                       'gaf', 'gene2go', 'taxid', 'dash_len', 'include_only',
                       'go_marks'])
    kws_dct_wr = set(['max_indent', 'no_indent', 'concise', 'relationship', 'dash_len'])

    def __init__(self, args=None, prt=sys.stdout):
        self.kws = DocOptParse(__doc__, self.kws_dct_all, self.kws_set_all).get_docargs(
            args, intvals=set(['max_indent', 'dash_len']))
        opt_attrs = OboOptionalAttrs.attributes.intersection(self.kws.keys())
        godag = get_godag(self.kws['dag'], prt, optional_attrs=opt_attrs)
        self.gene2gos = read_annotations(**self.kws)
        self.tcntobj = TermCounts(godag, self.gene2gos) if self.gene2gos is not None else None
        self._adj_go_marks()
        self.gosubdag = GoSubDag(godag.keys(), godag,
                                 relationships='relationship' in opt_attrs,
                                 tcntobj=self.tcntobj,
                                 children=True,
                                 prt=prt)
        self.goids = self._init_goids()

    def _init_goids(self):
        goids = GetGOs().get_goids(self.kws.get('GO'), self.kws.get('i'), sys.stdout)
        if goids:
            return goids
        # If GO DAG is small, print hierarchy for the entire DAG
        if len(self.gosubdag.go2nt) < 100:
            return set(self.gosubdag.go2nt.keys())

    def get_fouts(self):
        """Get output filename."""
        fouts_txt = []
        if 'o' in self.kws:
            fouts_txt.append(self.kws['o'])
        if 'f' in self.kws:
            fouts_txt.append(self._get_fout_go())
        return fouts_txt

    def _get_fout_go(self):
        """Get the name of an output file based on the top GO term."""
        assert self.goids, "NO VALID GO IDs WERE PROVIDED AS STARTING POINTS FOR HIERARCHY REPORT"
        base = next(iter(self.goids)).replace(':', '')
        upstr = '_up' if 'up' in self.kws else ''
        return "hier_{BASE}{UP}.{EXT}".format(BASE=base, UP=upstr, EXT='txt')

    def wrtxt_hier(self, fout_txt):
        """Write hierarchy below specfied GO IDs to an ASCII file."""
        with open(fout_txt, 'wb') as prt:
            self.prt_hier(prt)
            print("  WROTE: {TXT}".format(TXT=fout_txt))

    def prt_hier(self, prt=sys.stdout):
        """Write hierarchy below specfied GO IDs."""
        objwr = WrHierGO(self.gosubdag, **self.kws)
        assert self.goids, "NO VALID GO IDs WERE PROVIDED"
        if 'up' not in objwr.usrset:
            for goid in self.goids:
                objwr.prt_hier_down(goid, prt)
        else:
            objwr.prt_hier_up(self.goids, prt)

    def _adj_go_marks(self):
        """Adjust keywords, if needed."""
        if 'go_marks' in self.kws:
            # Process GO IDs specified in go_marks
            goids = self._get_goids(self.kws['go_marks'])
            # go_marks can take a list of GO IDs on cmdline or in a file.
            #     --go_marks=GO:0043473,GO:0009987
            #     --go_marks=go_marks.txt
            if goids:
                self.kws['go_marks'] = goids
            else:
                raise Exception("NO GO IDs FOUND IN go_marks")

        elif self.gene2gos:
            self.kws['go_marks'] = set(get_b2aset(self.gene2gos).keys())

    @staticmethod
    def _get_goids(gostr):
        """Return GO IDs from a GO str (e.g., GO:0043473,GO:0009987) or a file."""
        if 'GO:' in gostr:
            return gostr.split(',')
        elif os.path.exists(gostr):
            return GetGOs().get_goids(None, gostr, sys.stdout)


# Copyright (C) 2016-2018, DV Klopfenstein, H Tang. All rights reserved.
