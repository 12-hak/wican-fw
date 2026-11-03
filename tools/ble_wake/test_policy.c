#include <assert.h>
#include <math.h>
#include <stdio.h>
#include "ble_wake_test_policy.h"
int main(void)
{
    assert(ble_wake_test_decide(0,180000,true,12.3f,false)==0);
    assert(ble_wake_test_decide(10,180000,true,12.3f,true)==3);
    assert(ble_wake_test_decide(180000,180000,true,12.3f,false)==4);
    assert(ble_wake_test_decide(10,180000,true,11.99f,true)==5);
    assert(ble_wake_test_decide(10,180000,false,12.3f,true)==6);
    assert(ble_wake_test_decide(10,180000,true,NAN,true)==6);
    assert(ble_wake_test_decide(10,180000,true,INFINITY,true)==6);
    assert(ble_wake_test_decide(10,180000,true,12.0f,false)==0);
    assert(ble_wake_test_decide(180000,180000,true,11.5f,false)==5);
    puts("PASS: wait, authenticated wake, timeout, battery priority, ADC failure, finite voltage, cutoff boundary");
}
