#include <sancus/reactive.h>

#include <stdio.h>
#include <stdlib.h>

SM_OUTPUT(sm4, output4);


SM_ENTRY(sm4) void init(uint8_t* input_data, size_t len)
{
     puts("SM4 init");

     unsigned int val = 33;

     output4((unsigned char*) &val, sizeof(unsigned int));
}
