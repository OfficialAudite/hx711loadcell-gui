#!/usr/bin/env bash
# Lightweight Raspberry Pi optimization for HX711 sampling:
# - Forces CPU governor to performance on all cores.
# - Sets min freq to each core's max.
# - Leaves HX711 RATE pin selection to hardware (wire RATE high for ~80 Hz, low for ~10 Hz).
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run as root (sudo $0)" >&2
  exit 1
fi

echo "Setting CPU governor to performance..."
for gov_file in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
  [[ -f "$gov_file" ]] || continue
  echo performance >"$gov_file" || echo "Warn: cannot set $gov_file" >&2
done

echo "Raising min freq to max for all cores..."
for cpu_dir in /sys/devices/system/cpu/cpu*[0-9]; do
  maxf="$cpu_dir/cpufreq/scaling_max_freq"
  minf="$cpu_dir/cpufreq/scaling_min_freq"
  [[ -f "$maxf" && -f "$minf" ]] || continue
  mf=$(cat "$maxf")
  echo "$mf" >"$minf" || echo "Warn: cannot set $minf" >&2
done

echo "Done. Notes:"
echo "- HX711 RATE pin sets ADC speed: RATE low ~10 Hz (quieter), RATE high ~80 Hz (noisier)."
echo "- Keep wiring short/shielded; use a stable 5V/3V3 supply."
echo "- You can also start the app with 'sudo nice -n -5 python3 main.py' to lower scheduling latency."

