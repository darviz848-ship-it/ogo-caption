#!/bin/sh
# O'zbekcha transkripsiya o'lchovi - to'liq ketma-ketlik (HuggingFace ochiq bo'lishi shart).
#   sh bench/run_all.sh                 # Kotib/uzbek_stt_v1, barcha bitta-o'zgarishli sozlamalar
#   MODEL_REPO=<repo> TAG=<nom> sh bench/run_all.sh
# Natija: bench/out/<TAG>/{short,long}/*.json va bench/out/<TAG>/table.md
# To'xtab qolsa qayta ishga tushir - tayyor natijalar o'tkazib yuboriladi.
set -e
cd "$(dirname "$0")/.."
MODEL_REPO="${MODEL_REPO:-Kotib/uzbek_stt_v1}"
TAG="${TAG:-kotib_ct2_f16}"
MODEL_DIR="bench/models/$TAG"

python3 -m pip install -q -r bench/requirements.txt
python3 -I bench/prepare_fleurs.py
[ -f "$MODEL_DIR/model.bin" ] || python3 bench/convert_model.py "$MODEL_REPO" "$MODEL_DIR" --quantization float16

python3 bench/test_bench_lib.py

SINGLES="base prompt_none prompt_uz prompt_uz_ascii cond_off hst2 crt2.0 nst0.4 beam1 beam3 beam8 temp0 reppen1.1 nrng4 vad vad500 pp_premerge pp_dedup pp_noise"
ARGS=""
for c in $SINGLES; do ARGS="$ARGS --config $c"; done
# shellcheck disable=SC2086
python3 bench/run_bench.py --model "$MODEL_DIR" --tag "$TAG" --set short --limit 150 $ARGS
# shellcheck disable=SC2086
python3 bench/run_bench.py --model "$MODEL_DIR" --tag "$TAG" --set long $ARGS
python3 bench/summarize.py "$TAG"
echo
echo "Keyingi qadam: yaxshilagan sozlamalarni birlashtirib o'lcha, masalan:"
echo "  python3 bench/run_bench.py --model $MODEL_DIR --tag $TAG --set long --config base+cond_off+hst2+pp_premerge"
echo "Engine'ga kiritilgandan keyin: python3 bench/run_bench.py --model $MODEL_DIR --tag $TAG --set short --engine win/payload/Engine"
