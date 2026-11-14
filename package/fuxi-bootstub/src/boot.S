/* SPDX-License-Identifier: GPL-3.0-only */
/* Copyright (C) 2026 MaxXing */

  .section .text.init, "ax", @progbits
  .globl _start
  .option norvc
  .option norelax
_start:
  csrw mie, zero
  csrw mip, zero
  csrr a0, mhartid
  li a1, 0x87e00000
  li a2, 0
  li t0, 0x80000000
  jr t0
