//@ sm_output(output)
//@ sm_output(output2)


//@ sm_entry
pub fn entry(data : &[u8]) -> ResultMessage {
    info!("entry");

    output(data);

    success(None)
}

//@ sm_entry
pub fn entry2(data : &[u8]) -> ResultMessage {
    info!("entry2");

    output2(data);

    success(None)
}

//@ sm_entry
pub fn entry3(data : &[u8]) -> ResultMessage {
    info!("entry3");

    output(data);
    output2(data);

    success(None)
}
