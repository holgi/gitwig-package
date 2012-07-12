#!/bin/python
#
# rename it to gitwig-inbox, move it to your path and set the execution bit

import argparse
import gitwig
import markdown
import locale
import os
import subprocess

parser = argparse.ArgumentParser(description='processes the gitwig inbox')
parser.add_argument('-d', action="store_true", default=False, 
                    help="don't commit", dest='dont_commit')

parser.add_argument('-m', action="store", default="a gitwig update",
                    help="a commit message", metavar="message", dest='message')

args = parser.parse_args()


os.chdir("<path to live or local gitwig repository>")

locale.setlocale(locale.LC_ALL, 'de_DE')

gitwig.common.log.setLevel(20)

config = gitwig.settings.Settings.from_file("config.yaml")

inbox = gitwig.inbox.FolderInbox(config)
inbox.process()

if not args.dont_commit:
    subprocess.check_call(["git", "add", "-A"])
    subprocess.check_call(["git", "commit", "-m", args.message])
    subprocess.check_call(["git", "push", "origin", "master"])
