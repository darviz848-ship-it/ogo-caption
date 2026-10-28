#!/bin/bash
# OgoCaption - oflayn tarjima modelini o'rnatish. Ikki marta bosing.
cd "$(dirname "$0")" || exit 1
/bin/bash ./translate-model.sh "$@"
