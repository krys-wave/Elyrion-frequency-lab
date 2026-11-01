#!/bin/bash
cd "$(dirname "$0")" || exit 1
bash scripts/start.sh
lab_result=$?
if [[ "$lab_result" -ne 0 && "$lab_result" -ne 130 ]]; then
  printf '\nRead the startup message above. Run Setup Frequency Lab.command if needed.\n'
  read -r -p 'Press Return to close this window. ' _
fi
exit "$lab_result"
