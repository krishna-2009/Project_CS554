// Ticket lock safety harness: one ticket per thread, at most 3 serving polls.
// A bound-exhausted ticket remains unserved; no claim of liveness is made.
#include <threads.h>
#include <stdatomic.h>
#include <librace.h>
#include <model-assert.h>
#include <stdint.h>
atomic_int next_ticket, serving;
uint32_t payload;
bool acquired[2];
static void worker(void *arg) {
    const int i=(int)(intptr_t)arg;
    const int mine=atomic_fetch_add_explicit(&next_ticket,1,memory_order_relaxed);
    for (int k=0;k<3;++k) {
        if (atomic_load_explicit(&serving,memory_order_acquire)==mine) {
            acquired[i]=true;
            store_32(&payload,load_32(&payload)+1);
            atomic_store_explicit(&serving,mine+1,memory_order_release);
            return;
        }
    }
}
int user_main(int, char **) {
    thrd_t t[2]; atomic_init(&next_ticket,0); atomic_init(&serving,0);
    store_32(&payload,0); acquired[0]=acquired[1]=false;
    thrd_create(&t[0],worker,(void *)(intptr_t)0);
    thrd_create(&t[1],worker,(void *)(intptr_t)1);
    thrd_join(t[0]); thrd_join(t[1]);
    MODEL_ASSERT(load_32(&payload)==(uint32_t)(acquired[0]+acquired[1]));
    return 0;
}
