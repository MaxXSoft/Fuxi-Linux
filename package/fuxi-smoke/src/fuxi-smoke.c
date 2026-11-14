/* SPDX-License-Identifier: GPL-3.0-only */
/* Copyright (C) 2026 MaxXing */

#define _GNU_SOURCE
#include <errno.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static void fail(const char* message) {
  perror(message);
  exit(EXIT_FAILURE);
}

static int wait_child(pid_t child) {
  int status;
  pid_t result;
  do {
    result = waitpid(child, &status, 0);
  } while (result < 0 && errno == EINTR);

  if (result != child) fail("waitpid");
  return status;
}

static void memory_checks(void) {
  long page_size = sysconf(_SC_PAGESIZE);
  if (page_size != 4096) {
    fprintf(stderr, "Expected Sv32 4096-byte pages, got %ld\n", page_size);
    exit(EXIT_FAILURE);
  }

  volatile uint32_t* mapping =
      mmap(NULL, (size_t)page_size, PROT_READ | PROT_WRITE,
           MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (mapping == MAP_FAILED) fail("mmap");
  mapping[0] = 0x13579bdf;

  pid_t child = fork();
  if (child < 0) fail("fork for COW");
  if (child == 0) {
    if (mapping[0] != 0x13579bdf) _exit(10);
    mapping[0] = 0x2468ace0;
    if (mapping[0] != 0x2468ace0) _exit(11);
    execl("/bin/busybox", "busybox", "true", (char*)NULL);
    _exit(12);
  }

  int status = wait_child(child);
  if (!WIFEXITED(status) || WEXITSTATUS(status) != 0 ||
      mapping[0] != 0x13579bdf) {
    fprintf(stderr, "fork/exec or copy-on-write failed (status %#x)\n", status);
    exit(EXIT_FAILURE);
  }
  puts("FUXI_CHECK_PASS: fork exec copy-on-write");

  if (mprotect((void*)mapping, (size_t)page_size, PROT_READ)) {
    fail("mprotect");
  }

  child = fork();
  if (child < 0) fail("fork for protection fault");
  if (child == 0) {
    mapping[0] = 0;
    _exit(13);
  }

  status = wait_child(child);
  if (!WIFSIGNALED(status) || WTERMSIG(status) != SIGSEGV) {
    fprintf(stderr,
            "Write to read-only user page did not SIGSEGV (status %#x)\n",
            status);
    exit(EXIT_FAILURE);
  }

  if (munmap((void*)mapping, (size_t)page_size)) {
    fail("munmap");
  }

  puts("FUXI_CHECK_PASS: mmap mprotect SIGSEGV");
}

static void misaligned_checks(void) {
  _Alignas(4) unsigned char bytes[8] = {0, 0x11, 0x22, 0x33, 0x44, 0, 0, 0};
  uint32_t loaded;
  uint32_t value = 0xa1b2c3d4;

  /* Force scalar accesses, rather than relying on undefined C alignment. */
  __asm__ volatile("lw %0, 1(%1)" : "=r"(loaded) : "r"(bytes) : "memory");
  if (loaded != 0x44332211) {
    fprintf(stderr, "Misaligned lw returned %#x\n", loaded);
    exit(EXIT_FAILURE);
  }

  __asm__ volatile("sw %0, 1(%1)" : : "r"(value), "r"(bytes) : "memory");
  if (bytes[0] != 0 || bytes[1] != 0xd4 || bytes[2] != 0xc3 ||
      bytes[3] != 0xb2 || bytes[4] != 0xa1 || bytes[5] != 0) {
    fprintf(stderr, "Misaligned sw corrupted the byte pattern\n");
    exit(EXIT_FAILURE);
  }

  puts("FUXI_CHECK_PASS: misaligned lw sw");
}

static void timer_checks(void) {
  struct timespec before, after, remaining = {.tv_sec = 0, .tv_nsec = 20000000};

  if (clock_gettime(CLOCK_MONOTONIC, &before)) {
    fail("clock_gettime before");
  }

  while (nanosleep(&remaining, &remaining)) {
    if (errno != EINTR) fail("nanosleep");
  }

  if (clock_gettime(CLOCK_MONOTONIC, &after)) {
    fail("clock_gettime after");
  }

  int64_t elapsed = (int64_t)(after.tv_sec - before.tv_sec) * 1000000000 +
                    (int64_t)after.tv_nsec - before.tv_nsec;
  if (elapsed < 20000000) {
    fprintf(stderr, "Timer returned early: %lld ns\n", (long long)elapsed);
    exit(EXIT_FAILURE);
  }

  puts("FUXI_CHECK_PASS: clock_gettime nanosleep");
}

int main(void) {
  setvbuf(stdout, NULL, _IONBF, 0);
  memory_checks();
  misaligned_checks();
  timer_checks();
  return EXIT_SUCCESS;
}
