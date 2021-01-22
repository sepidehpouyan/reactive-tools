//@ sm_input
pub fn input2(data : &[u8]) {
    info!("input");

    if data.len() < 2 {
        error!("Wrong data received");
        return;
    }

    let val = u16::from_le_bytes([data[0], data[1]]);

    info!(&format!("Val: {}", val));
}

//@ sm_entry
pub fn entry(data : &[u8]) -> ResultMessage {
    info!("entry");

    success(None)
}
