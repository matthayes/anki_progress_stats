#!/usr/bin/env bash

ROOT_DIR=$(pwd)
TARGET_DIR=$ROOT_DIR/target
rm -rf $TARGET_DIR
mkdir -p $TARGET_DIR
TEMP_DIR=`mktemp -d`
echo Using temp dir $TEMP_DIR
cp __init__.py $TEMP_DIR
cp manifest.json $TEMP_DIR
mkdir $TEMP_DIR/progress_stats
cp progress_stats/__init__.py $TEMP_DIR/progress_stats
cp progress_stats/compute.py $TEMP_DIR/progress_stats
cp progress_stats/graphs.py $TEMP_DIR/progress_stats
pushd $TEMP_DIR
zip -r anki_progress_stats.zip .
echo Moving package to $TARGET_DIR
mv anki_progress_stats.zip $TARGET_DIR
popd
rm -rf $TEMP_DIR