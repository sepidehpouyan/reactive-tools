#include <sancus/reactive.h>

#include <stdio.h>
#include <stdlib.h>

SM_OUTPUT(sm2, output);
SM_OUTPUT(sm2, output2);


SM_ENTRY(sm2) void init(uint8_t* input_data, size_t len)
{
     puts("SM2 init\n");

     unsigned int val = 33;

     output((unsigned char*) &val, sizeof(unsigned int));
}

SM_ENTRY(sm2) void init2(uint8_t* input_data, size_t len)
{
     puts("SM2 init2\n");

     unsigned int val = 33;

     output((unsigned char*) &val, sizeof(unsigned int));
     output2((unsigned char*) &val, sizeof(unsigned int));
}
