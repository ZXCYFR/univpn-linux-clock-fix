#define _POSIX_C_SOURCE 200809L
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <time.h>

/* 测量稳定的 CPU 时间戳计数器，不改变 CPU 频率或电源设置。 */
static uint64_t counter(void) {
    unsigned int low, high;
    __asm__ volatile("lfence; rdtsc" : "=a"(low), "=d"(high) :: "memory");
    return ((uint64_t)high << 32) | low;
}

static double seconds(struct timespec t) {
    return t.tv_sec + t.tv_nsec / 1e9;
}

int main(void) {
    for (int sample = 0; sample < 3; sample++) {
        struct timespec before, after, delay = {0, 500000000};
        if (clock_gettime(CLOCK_MONOTONIC_RAW, &before)) return 1;
        uint64_t start = counter();
        if (nanosleep(&delay, NULL)) return 1;
        uint64_t stop = counter();
        if (clock_gettime(CLOCK_MONOTONIC_RAW, &after)) return 1;
        double elapsed = seconds(after) - seconds(before);
        printf("实际计时时钟 MHz: %.3f，采样间隔: %.6f 秒\n", (stop-start)/elapsed/1e6, elapsed);
    }
    return 0;
}
