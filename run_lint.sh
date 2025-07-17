#!/bin/bash
cd /Users/archmagece/myopen/scripton/sb-kube-app-manager
make lint > lint-output.txt 2>&1
echo "Exit code: $?" >> lint-output.txt