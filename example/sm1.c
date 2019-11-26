#include <sancus/reactive.h>

#include <stdio.h>

#include "/home/job/phd/sancus/contiki-support/examples/sm-server/buttons_driver.h"

SM_OUTPUT(sm1, output);

SM_ENTRY(sm1) void on_button_event(int pressed)
{
    if (sancus_get_caller_id() != *SM_GET_VERIFY_ID(sm1, buttons_driver))
    {
        //puts("Illegal caller");
        return;
    }

    output(&pressed, sizeof(pressed));
}

SM_ENTRY(sm1) void init(uint8_t* input_data, size_t len)
{
//     puts("SM1 init");

    sm_id driver_id = sancus_verify_address(input_data,
                                            SM_GET_ENTRY(buttons_driver));

    if (driver_id == 0)
    {
        //puts("Driver verification failed");
        return;
    }

    *SM_GET_VERIFY_ID(sm1, buttons_driver) = driver_id;

    //puts("Registering callback");
    buttons_driver_register_callback(Button1,
                                     SM_GET_ENTRY(sm1),
                                     SM_GET_ENTRY_IDX(sm1, on_button_event));
    //puts("Done");
}
