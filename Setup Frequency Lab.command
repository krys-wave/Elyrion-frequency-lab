#!/bin/bash
cd "$(dirname "$0")" || exit 1
lab_result=0
if bash scripts/install.sh; then
  printf '\nSetup complete. Open Start Frequency Lab.command to launch.\n'
else
  lab_result=1
  printf '\nSetup needs attention. Read the message above and docs/macos.md.\n'
fi
read -r -p 'Press Return to close this window. ' _
exit "$lab_result"
