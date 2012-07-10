#!/bin/sh

echo
echo "**** Pulling changes into Live [Bares's post-update hook]"
echo

cd <path to live repository > || exit
unset GIT_DIR
git pull <path to hub repository> master
