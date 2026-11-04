/* Bounded TCP stream writes. No ESP dependencies: tested with scripted short writes/errors. */
#pragma once
#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
#include <errno.h>

typedef int (*sm_write_fn)(void *, const uint8_t *, size_t, int *);
typedef uint64_t (*sm_clock_fn)(void *);
typedef void (*sm_wait_fn)(void *);
typedef struct { size_t sent; int error; bool timed_out; } sm_write_result;

static inline sm_write_result sm_write_all(void *ctx, const uint8_t *data, size_t len,
    uint64_t budget_ms, sm_write_fn write_fn, sm_clock_fn clock_fn, sm_wait_fn wait_fn)
{
    sm_write_result r = {0};
    uint64_t started = clock_fn(ctx);
    while (r.sent < len) {
        if (clock_fn(ctx) - started >= budget_ms) {
            r.error = ETIMEDOUT; r.timed_out = true; break;
        }
        int error = 0;
        int n = write_fn(ctx, data + r.sent, len - r.sent, &error);
        if (n > 0 && (size_t)n <= len - r.sent) { r.sent += (size_t)n; continue; }
        if (n == 0) { r.error = ECONNRESET; break; }
        if (n > 0) { r.error = EIO; break; }
        if (error == EINTR) continue;
        if (error == EAGAIN || error == EWOULDBLOCK) { wait_fn(ctx); continue; }
        r.error = error ? error : EIO; break;
    }
    return r;
}
