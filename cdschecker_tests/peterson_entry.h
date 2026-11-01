// Bounded Peterson doorway: two threads, one observation each, no unlock.
// Entry decisions are private until join; no shared monitor RMW repairs the lock.
#include <threads.h>
#include <stdatomic.h>
#include <model-assert.h>
#include <stdint.h>
atomic_int flag[2], turn;
bool entered[2];
static void worker(void *arg) {
    const int i = (int)(intptr_t)arg, j = 1-i;
    atomic_store_explicit(&flag[i], 1, STORE_ORDER);
    atomic_store_explicit(&turn, j, STORE_ORDER);
    const int other = atomic_load_explicit(&flag[j], LOAD_ORDER);
    const int victim = atomic_load_explicit(&turn, LOAD_ORDER);
    entered[i] = !other || victim != j;
}
int user_main(int, char **) {
    thrd_t t[2];
    atomic_init(&flag[0], 0); atomic_init(&flag[1], 0); atomic_init(&turn, 0);
    entered[0] = entered[1] = false;
    thrd_create(&t[0], worker, (void *)(intptr_t)0);
    thrd_create(&t[1], worker, (void *)(intptr_t)1);
    thrd_join(t[0]); thrd_join(t[1]);
    MODEL_ASSERT(!(entered[0] && entered[1]));
    return 0;
}
