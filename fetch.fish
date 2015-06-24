#!/usr/local/bin/fish
vf activate awwniview
set -x PYTHONPATH /usr/local/lib/python2.7/site-packages
python danboopagefetch.py
python awwniget.py
python awwnifetch.py
