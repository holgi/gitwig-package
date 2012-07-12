#!/bin/sh
#
# To enable this hook, rename this file to "post-merge".

echo "starting website rendering, have a look at gitwig.log"
nohup gitwig-update > gitiwg.log 2>&1 &
