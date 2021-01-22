#include <sancus/reactive.h>

#include <stdio.h>

SM_INPUT(sm3, input3, data, len)
{
  if(len < 2) {
    puts("SM3 input3: Wrong data");
    return;
  }

  unsigned int val = *(unsigned int*) data;

  if(val == 33) {
    puts("SM3 input3: Correct!");
  }
  else {
    puts("SM3 input3: Wrong");
  }
}

SM_ENTRY(sm3) void init(uint8_t* input_data, size_t len)

{
    (void) input_data;
    (void) len;
     puts("hello from sm3");
}
