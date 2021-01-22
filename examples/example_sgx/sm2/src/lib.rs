
//@ sm_input
pub fn input(_data : &[u8]) {
    info!("input");
}

//@ sm_input
pub fn input2(_data : &[u8]) {
    info!("input2");
}

//@ sm_entry
pub fn entry(data : &[u8]) -> ResultMessage {
    info!("entry");

    success(None)
}
