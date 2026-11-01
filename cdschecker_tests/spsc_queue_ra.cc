// One-slot SPSC publication harness: one item, one attempt, no slot reuse.
// This tests the core release/acquire publication edge, not a complete ring buffer.
#include <threads.h>
#include <stdatomic.h>
#include <librace.h>
#include <model-assert.h>
#include <stdint.h>
atomic_int ready;
uint32_t slot;
static void producer(void *) {
    store_32(&slot,42);
    atomic_store_explicit(&ready,1,memory_order_release);
}
static void consumer(void *) {
    if (atomic_load_explicit(&ready,memory_order_acquire)==1)
        MODEL_ASSERT(load_32(&slot)==42);
}
int user_main(int, char **) {
    thrd_t p,c; atomic_init(&ready,0); store_32(&slot,0);
    thrd_create(&p,producer,0); thrd_create(&c,consumer,0);
    thrd_join(p); thrd_join(c); return 0;
}
