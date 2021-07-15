//@ sm_output(button_pressed)


//@ sm_entry
pub fn entry(data : &[u8]) -> ResultMessage {
    info!("Button has been pressed, sending output");

    button_pressed(&[]);

    success(None)
}
