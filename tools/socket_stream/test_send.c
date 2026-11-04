#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "../../components/socket_manager/socket_send_all.h"
typedef struct { int steps[32]; int count, at; uint64_t ms; uint8_t out[256]; size_t used; } fake;
static int write_fake(void *ctx, const uint8_t *p, size_t n, int *error) {
    fake *f=ctx;f->ms+=2;
    int step=f->at < f->count ? f->steps[f->at++] : (int)n;
    if(step<0){*error=-step;return -1;}
    if((size_t)step>n)step=(int)n;
    memcpy(f->out+f->used,p,step);f->used+=step;return step;
}
static uint64_t now(void *ctx){return ((fake*)ctx)->ms;}
static void wait(void *ctx){((fake*)ctx)->ms+=10;}
int main(void){
    const uint8_t bytes[]="a GVRET stream must keep every byte in order";
    fake f={.steps={3,-EINTR,2,-EAGAIN,4},.count=5};
    sm_write_result r=sm_write_all(&f,bytes,sizeof(bytes),500,write_fake,now,wait);
    assert(r.sent==sizeof(bytes)&&r.error==0&&!r.timed_out);
    assert(memcmp(bytes,f.out,sizeof(bytes))==0);
    f=(fake){.steps={4,-ECONNRESET},.count=2};
    r=sm_write_all(&f,bytes,sizeof(bytes),500,write_fake,now,wait);
    assert(r.sent==4&&r.error==ECONNRESET&&!r.timed_out);
    f=(fake){.steps={0},.count=1};
    r=sm_write_all(&f,bytes,sizeof(bytes),500,write_fake,now,wait);
    assert(r.sent==0&&r.error==ECONNRESET);
    f=(fake){.count=32};for(int i=0;i<32;i++)f.steps[i]=-EAGAIN;
    r=sm_write_all(&f,bytes,sizeof(bytes),100,write_fake,now,wait);
    assert(r.sent==0&&r.timed_out&&r.error==ETIMEDOUT&&f.ms<=112);
    f=(fake){0};r=sm_write_all(&f,bytes,0,500,write_fake,now,wait);
    assert(r.sent==0&&r.error==0);
    puts("PASS: partial writes, interrupted writes, temporary backpressure, hard error, closed peer, deadline, empty write");
}
