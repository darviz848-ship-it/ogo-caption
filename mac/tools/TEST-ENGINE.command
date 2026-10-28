#!/bin/bash
# OgoCaption - o'rnatilgan enjinni tekshirish. Ikki marta bosing.
cd "$(dirname "$0")" || exit 1
/bin/bash ./test-engine.sh "$@"
