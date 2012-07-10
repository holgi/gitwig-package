#!/bin/sh
#
# An example hook script to prepare a packed repository for use over
# dumb transports.
#
# To enable this hook, rename this file to "post-merge".

echo "starting website rendering, have a look at gitwig.log"
nohup gitwig-update > gitiwg.log 2>&1 &
