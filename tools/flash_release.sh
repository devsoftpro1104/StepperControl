#!/usr/bin/env bash
# Прошивка релизного билда с помощью OpenOCD (ST-Link v2/v3).
set -euo pipefail

ELF="${1:-firmware/build/release/stepper_control_fw.elf}"
openocd -f interface/stlink.cfg -f target/stm32f4x.cfg \
  -c "program ${ELF} verify reset exit"