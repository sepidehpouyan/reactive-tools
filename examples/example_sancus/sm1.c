#include <sancus/reactive.h>

#include <stdio.h>

SM_INPUT(sm1, input, data, len)
{
  puts("SM1 input!");

  if(len != sizeof(unsigned int)) {
    puts("Wrong data received!");
    return;
  }

  unsigned int val = *(unsigned int*) data;

  if(val == 33) {
    puts("SM1 input Correct!");
  }
  else {
    puts("SM1 input Wrong");
  }
}

SM_INPUT(sm1, input2, data, len)
{
  puts("SM1 input2!");

  if(len != sizeof(unsigned int)) {
    puts("Wrong data received!");
    return;
  }

  unsigned int val = *(unsigned int*) data;

  if(val == 33) {
    puts("SM1 input2 Correct!");
  }
  else {
    puts("SM1 input2 Wrong");
  }
}

SM_ENTRY(sm1) void init(uint8_t* input_data, size_t len)

{
    (void) input_data;
    (void) len;
     puts("hello from sm1");
}
