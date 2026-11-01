// Bounded one-acquisition Peterson race probe, at most two guard checks.
// A failed bounded attempt withdraws its flag. This checks safety, not progress.
#include <threads.h>
#include <stdatomic.h>
#include <librace.h>
#include <stdint.h>
atomic_int flag[2], turn;
uint32_t payload;
static void worker(void *arg) {
    const int i = (int)(intptr_t)arg, j = 1-i;
    atomic_store_explicit(&flag[i], 1, STORE_ORDER);
    atomic_store_explicit(&turn, j, STORE_ORDER);
    for (int k=0; k<2; ++k) {
        const int other = atomic_load_explicit(&flag[j], LOAD_ORDER);
        const int victim = atomic_load_explicit(&turn, LOAD_ORDER);
        if (!other || victim != j) {
            store_32(&payload, (uint32_t)(i+1));
            atomic_store_explicit(&flag[i], 0, STORE_ORDER);
            return;
        }
    }
    atomic_store_explicit(&flag[i], 0, STORE_ORDER);
}
int user_main(int, char **) {
    thrd_t t[2];
    atomic_init(&flag[0], 0); atomic_init(&flag[1], 0); atomic_init(&turn, 0);
    store_32(&payload, 0);
    thrd_create(&t[0], worker, (void *)(intptr_t)0);
    thrd_create(&t[1], worker, (void *)(intptr_t)1);
    thrd_join(t[0]); thrd_join(t[1]);
    return 0;
}
