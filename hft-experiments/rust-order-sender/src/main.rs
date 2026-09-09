use std::io::{self, Write};
use std::net::UdpSocket;
use std::time::{SystemTime, UNIX_EPOCH};

#[repr(C)]
#[derive(Clone, Copy)]
struct OrderPacket {
    version: u8,     // protocol version
    side: u8,        // 0 = buy, 1 = sell
    token: u32,      // token / instrument id
    amount: i64,     // fixed-point (e.g. *1e8)
    price: i64,      // fixed-point
    nonce: u64,      // unique per order
}

fn read<T: std::str::FromStr>(prompt: &str) -> T {
    loop {
        print!("{}", prompt);
        io::stdout().flush().unwrap();

        let mut buf = String::new();
        io::stdin().read_line(&mut buf).unwrap();

        if let Ok(v) = buf.trim().parse::<T>() {
            return v;
        }

        println!("Invalid input, try again.");
    }
}

fn main() -> io::Result<()> {
    println!("=== Order Creator ===");

    let side_str: String = read("Side (buy/sell): ");
    let side = match side_str.as_str() {
        "buy" => 0,
        "sell" => 1,
        _ => {
            println!("Invalid side");
            return Ok(());
        }
    };

    let token: u32 = read("Token ID (u32): ");
    let amount: i64 = read("Amount (fixed-point int): ");
    let price: i64 = read("Price (fixed-point int): ");

    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos() as u64;

    let order = OrderPacket {
        version: 1,
        side,
        token,
        amount,
        price,
        nonce,
    };

    // Bind locally (ephemeral port)
    let socket = UdpSocket::bind("0.0.0.0:0")?;

    // Destination: XDP-enabled UDP port on peer
    let target = "192.168.1.100:9000"; // <-- other node

    let bytes = unsafe {
        std::slice::from_raw_parts(
            &order as *const OrderPacket as *const u8,
            std::mem::size_of::<OrderPacket>(),
        )
    };

    socket.send_to(bytes, target)?;

    println!("Order sent:");
    println!("  side   = {}", if side == 0 { "BUY" } else { "SELL" });
    println!("  token  = {}", token);
    println!("  amount = {}", amount);
    println!("  price  = {}", price);
    println!("  nonce  = {}", nonce);

    Ok(())
}
