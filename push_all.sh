#!/bin/bash
# push_all.sh — tif verilerini senaryo bazinda parcalayip GitHub'a push eder.
#
# Calistir (kapak ACIK, uykuyu caffeinate engeller):
#   chmod +x push_all.sh
#   caffeinate -i nohup ./push_all.sh > push_log.txt 2>&1 &
#   tail -f push_log.txt      # ilerlemeyi izle (Ctrl+C ile cikinca arkada surer)
#
# Bitti mi:  grep "ALL DONE" push_log.txt

set -e  # bir push hata verirse dur (yarim birakmasin)
cd "$(dirname "$0")"

echo "===== START: $(date) ====="

echo "----- historical -----"
git add data/indices/historical/
git commit -m "Data: historical TIFFs — TR-clipped, 1995-2014, +AT/ESI/PPD, cleanup" || echo "(historical: commit edilecek degisiklik yok)"
git push origin main
echo "===== historical DONE: $(date) ====="

echo "----- ssp126 -----"
git add data/indices/future/ssp126/
git commit -m "Data: SSP126 TIFFs — TR-clipped, updated" || echo "(ssp126: commit edilecek degisiklik yok)"
git push origin main
echo "===== ssp126 DONE: $(date) ====="

echo "----- ssp245 (UHI dahil, en buyuk) -----"
git add data/indices/future/ssp245/
git commit -m "Data: SSP245 TIFFs — TR-clipped + UHI variants" || echo "(ssp245: commit edilecek degisiklik yok)"
git push origin main
echo "===== ssp245 DONE: $(date) ====="

echo "----- ssp585 -----"
git add data/indices/future/ssp585/
git commit -m "Data: SSP585 TIFFs — TR-clipped, updated" || echo "(ssp585: commit edilecek degisiklik yok)"
git push origin main
echo "===== ssp585 DONE: $(date) ====="

echo "===== ALL DONE: $(date) ====="