#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

""" tvideo - generate a javascript text video from a custom source markup file

sample format:

Yadda yadda
:p4
This will be shown after 4s pause

:type
This text will be shown with typewriter effect

copyright (c) 2014 lightbird.net
"""

from __future__ import print_function, unicode_literals, division
import os, sys
import re
from os.path import join as pjoin
from os.path import split as psplit
from os.path import splitext
from json import dumps
from html import escape

from utils import getitem, first, nl, space, multi_replace


# :hN - header; :pN - pause
cmdpat         = r"""(
                          \n:(pause)\ ?(\d*)
                        | \n:(clear)
                        | \n:(type)
                        | \n:(q)
                        | \n:(h\d+)\ ([^\n]+)
                        | \n:(note)\ ([^\n]+)
                        | \n:(p)(\d*)
                        | \n:(\d+)
                        )"""

# re.split() adds matched groups if present, so we need to remove all inner groups
splitpat       = "(%s)" % cmdpat.replace(')','').replace('(','')
imgpat         = r"(\[img:[A-Za-z0-9.]+])"
tut_dir        = "src/"
outdir         = "out/"
tplfn          = "template.html"
nbsp           = "&nbsp;"
space          = ' '
endmsg         = "--- THE END ---".center(79)
interp_typecmd = True   # auto insert type effect before python interpreter lines (>>>)
nl             = '\n'
images         = []

for fn in os.listdir("out/img"):
    # images.append((fn, "<img src='img/%s' height='32' style='padding-bottom:10px' />" % fn))
    name = splitext(fn)[0]
    images.append((name, fn, "<img src='img/%s' height='32' />" % fn))


class Tutorial(object):
    typeblock = False

    def __init__(self, fn, tpl):
        """Split file contents into sections."""
        self.commands = []
        self.name     = first( splitext( psplit(fn)[1] ) )
        self.tpl      = tpl

        with open(fn, encoding="utf-8") as fp:
            self.sections = re.split(splitpat, fp.read(), flags=re.VERBOSE)

    def run(self):
        """Add each section to `self.commands` and write html."""
        add = self.add_text
        add(nl * 2)
        sections = [s for s in self.sections if s is not None]

        for section in sections:
            # print ("section", section)
            match = re.match(cmdpat, section, re.VERBOSE)
            if match:
                match = list(filter(None, match.groups()))
                cmd   = match[1]
                arg   = getitem(match, 2)
                if cmd == 'q':
                    break
                if cmd == 'p': cmd = "pause"
                if cmd.isdigit() and not arg:
                    arg = cmd
                    cmd = "pause"

                if cmd == "pause":
                    arg = arg or default_pause
                if cmd == "note":
                    arg = "Note: " + arg
                self.commands.append(dict(cmd=cmd, arg=arg))
            else:
                add(section)

        add(nl*3 + endmsg + nl*2)
        self.write_html()
        print("%s written.." % self.name)

    def write_html(self):
        """Insert commands into template and write html."""
        cmds  = dumps(self.commands, indent=4, separators=(',', ':'))
        html  = self.tpl.replace("%COMMANDS%", cmds)
        html = html.replace("%TITLE%", self.name.capitalize())
        outfn = pjoin(outdir, self.name + ".html")

        # for c in self.commands: print(c)
        with open(outfn, 'w', encoding="utf-8") as fp:
            fp.write(html)

    def add_text(self, text):
        """ Add each line in text to commands; auto-insert type command for interpreter blocks.
            (also insert images)
        """
        if text.startswith(nl):
            text = text[1:]

        cls           = ''
        prefix        = ''
        is_code       = False
        is_output     = False
        code_indent   = 0
        interp_line   = False
        after_blank   = False     # state 'after blank line'
        blank         = False
        output_indent = 0

        for line in text.split(nl):
            if line.strip().startswith('#'):
                continue
            line   = line.rstrip()
            blank  = bool(not line)
            indent = len(line) - len(line.lstrip()) + 1

            if interp_typecmd and line.strip().startswith(">>>"):
                self.commands.append(dict(cmd="type", arg=None))
                cls           = "code"
                prefix        = escape(">>>") + nbsp
                is_code       = True
                interp_line   = True
                # interp.prompt, space, 1 level of block indent
                code_indent   = indent + 3+1
                output_indent = code_indent - 4

            # blank line; next line at code indent: still code; ELSE reset code
            # non-blank line; next line at code indent - 4: output

            # shorter indent than code should be means end of code block; ignore blank lines
            if not interp_line and indent < code_indent and not blank:
                is_code = False; cls = ''

            if not interp_line and after_blank and indent != code_indent and not blank:
                is_code = False; cls = ''

            if indent==output_indent and not interp_line:
                is_output = True; cls = "output"

            if is_output and indent < output_indent:
                is_output = False; cls = ''

            # ugly hack: force bigger indent on lines of code except for interp lines
            if is_code and not interp_line:
                indent += 4

            line = line.lstrip("> ")
            arg  = escape(line)
            arg  = arg.replace(space, nbsp).replace("--", "&mdash;")
            if is_code or is_output:
                for name, fn, tag in images:
                    arg = arg.replace(name+"png", fn)
                    arg = arg.replace(fn, tag)
            self.commands.append( dict(cmd="text", arg=arg, indent=indent, cls=cls, prefix=prefix) )
            prefix      = ''
            interp_line = False
            after_blank = bool(not line.strip())


class TutorialMovies(object):
    def run(self, fnames):

        if not fnames:
            fnames = [pjoin(tut_dir, fn) for fn in os.listdir(tut_dir) if not fn.startswith('.')]
        tpl = open(tplfn).read()

        for fn in fnames:
            Tutorial(fn, tpl).run()


if __name__ == "__main__":
    arg = sys.argv
    del arg[0]
    try                      : TutorialMovies().run(arg)
    except KeyboardInterrupt : pass
