mod artifacts;
mod bridge;
mod config;
mod runner;
mod types;

use crate::config::RunConfig;

fn main() {
    let config = match RunConfig::from_env_args(std::env::args().skip(1)) {
        Ok(config) => config,
        Err(err) => {
            eprintln!("{err}");
            std::process::exit(64);
        }
    };
    if let Err(err) = runner::run(config) {
        eprintln!("{err}");
        std::process::exit(1);
    }
}
