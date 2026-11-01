// TAS bounded try-lock: each thread attempts once; success protects a payload.
#include <threads.h>
#include <stdatomic.h>
#include <librace.h>
#include <model-assert.h>
#include <stdint.h>
atomic_int locked;
uint32_t payload;
bool acquired[2];
static void worker(void *arg) {
    const int i = (int)(intptr_t)arg;
    acquired[i] = atomic_exchange_explicit(&locked, 1, memory_order_acquire) == 0;
    if (acquired[i]) {
        const uint32_t before = load_32(&payload);
        store_32(&payload, before+1);
        atomic_store_explicit(&locked, 0, memory_order_release);
    }
}
int user_main(int, char **) {
    thrd_t t[2]; atomic_init(&locked,0); store_32(&payload,0);
    acquired[0]=acquired[1]=false;
    thrd_create(&t[0], worker, (void *)(intptr_t)0);
    thrd_create(&t[1], worker, (void *)(intptr_t)1);
    thrd_join(t[0]); thrd_join(t[1]);
    MODEL_ASSERT(load_32(&payload) == (uint32_t)(acquired[0]+acquired[1]));
    return 0;
}
