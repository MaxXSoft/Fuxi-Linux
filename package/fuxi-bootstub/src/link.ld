/* SPDX-License-Identifier: GPL-3.0-only */
/* Copyright (C) 2026 MaxXing */

OUTPUT_ARCH(riscv)
ENTRY(_start)
SECTIONS {
  . = 0x200;
  .text : { KEEP(*(.text.init)) *(.text*) }
  /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
