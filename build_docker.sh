#!/bin/sh

set -e

echo "Building container tagged deaddocker. This will take some time..." 
docker build . -t deaddocker

echo "Creating docker volume named deadpersistent..." 
docker volume create deadpersistent

echo "Preparing volume..."
docker run -it \
    -v deadpersistent:/persistent\
    -v $(realpath ./patches/):/patches \
    deaddocker \
    sudo su -c "cp /patches/patchdb.json /persistent/patchdb.json &&\
                mkdir /persistent/logs && mkdir /persistent/compiler_cache &&\
                chown dead:dead -R /persistent"
docker run -it \
    -v deadpersistent:/persistent\
    deaddocker \
    sh -c "chmod 770 /persistent/compiler_cache &&\
           chmod g+rws /persistent/compiler_cache"

docker run -it \
    -v deadpersistent:/persistent\
    deaddocker \
    sh -c "touch /persistent/casedb.sqlite3"

docker run -it \
    -v deadpersistent:/persistent\
    deaddocker \
    sh -c "cd /persistent && git clone git://gcc.gnu.org/git/gcc.git"

docker run -it \
    -v deadpersistent:/persistent\
    deaddocker \
    sh -c "cd /persistent && git clone https://github.com/llvm/llvm-project"
