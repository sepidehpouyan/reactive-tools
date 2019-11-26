#include <sancus/reactive.h>

#include <stdio.h>

#include "/home/job/phd/sancus/contiki-support/examples/sm-server/lcd_driver.h"

SM_INPUT(sm2, input, data, len)
{
    int pressed = *(int*)data;
    lcd_driver_write(pressed ? "P" : "R");
}

SM_ENTRY(sm2) void init(uint8_t* input_data, size_t len)
{
//     puts("SM2 init");

    sm_id driver_id = sancus_verify_address(input_data,
                                            SM_GET_ENTRY(lcd_driver));

    if (driver_id == 0)
    {
//         puts("Driver verification failed");
        return;
    }

    *SM_GET_VERIFY_ID(sm2, lcd_driver) = driver_id;
    lcd_driver_acquire();
}
