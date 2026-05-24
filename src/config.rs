use std::collections::BTreeSet;
use std::path::PathBuf;

#[derive(Debug, Clone)]
pub struct RunConfig {
    pub run_id: String,
    pub run_name: String,
    pub env: String,
    pub version: String,
    pub leaderboard: bool,
    pub fail_fast: bool,
    pub workers: usize,
    pub tasks: Vec<String>,
    pub artifact_dir: PathBuf,
    pub enabled_rules: BTreeSet<String>,
    pub max_wall_sum_seconds: Option<f64>,
}

impl RunConfig {
    pub fn from_env_args<I>(args: I) -> Result<Self, String>
    where
        I: IntoIterator<Item = String>,
    {
        let mut config = Self::default();
        let mut iter = args.into_iter();
        while let Some(arg) = iter.next() {
            match arg.as_str() {
                "run" => {}
                "--run-id" => config.run_id = need_value(&mut iter, &arg)?,
                "--run-name" => config.run_name = need_value(&mut iter, &arg)?,
                "--env" => config.env = need_value(&mut iter, &arg)?.to_ascii_lowercase(),
                "--version" => config.version = need_value(&mut iter, &arg)?,
                "--leaderboard" => config.leaderboard = parse_bool(&need_value(&mut iter, &arg)?)?,
                "--fail-fast" => config.fail_fast = parse_bool(&need_value(&mut iter, &arg)?)?,
                "--workers" => {
                    config.workers = parse_usize(&need_value(&mut iter, &arg)?, "workers")?
                }
                "--tasks" => config.tasks = parse_tasks(&need_value(&mut iter, &arg)?),
                "--artifact-dir" => {
                    config.artifact_dir = PathBuf::from(need_value(&mut iter, &arg)?)
                }
                "--rules" => config.enabled_rules = parse_rules(&need_value(&mut iter, &arg)?),
                "--max-wall-sum-seconds" => {
                    config.max_wall_sum_seconds = Some(parse_f64(
                        &need_value(&mut iter, &arg)?,
                        "max-wall-sum-seconds",
                    )?)
                }
                "--help" | "-h" => return Err(help()),
                other => return Err(format!("unknown argument: {other}\n{}", help())),
            }
        }
        if config.tasks.is_empty() {
            config.tasks = (1..=5).map(|n| format!("t{n:02}")).collect();
        }
        let supported_envs = ["ecom", "pac1", "pac1-prod"];
        if !supported_envs.contains(&config.env.as_str()) {
            return Err(format!("unsupported env: {}", config.env));
        }
        Ok(config)
    }
}

impl Default for RunConfig {
    fn default() -> Self {
        let rules = ["catalog", "inventory", "security"];
        Self {
            run_id: format!("det-{}", unixish_stamp()),
            run_name: String::new(),
            env: "ecom".to_string(),
            version: env!("CARGO_PKG_VERSION").to_string(),
            leaderboard: false,
            fail_fast: false,
            workers: 1,
            tasks: Vec::new(),
            artifact_dir: PathBuf::from("runs"),
            enabled_rules: rules.into_iter().map(String::from).collect(),
            max_wall_sum_seconds: None,
        }
    }
}

fn need_value<I>(iter: &mut I, name: &str) -> Result<String, String>
where
    I: Iterator<Item = String>,
{
    iter.next()
        .ok_or_else(|| format!("missing value for {name}"))
}

fn parse_bool(value: &str) -> Result<bool, String> {
    match value.to_ascii_lowercase().as_str() {
        "1" | "true" | "yes" | "on" => Ok(true),
        "0" | "false" | "no" | "off" => Ok(false),
        _ => Err(format!("invalid bool: {value}")),
    }
}

fn parse_usize(value: &str, name: &str) -> Result<usize, String> {
    value
        .parse::<usize>()
        .map_err(|_| format!("invalid {name}: {value}"))
}

fn parse_f64(value: &str, name: &str) -> Result<f64, String> {
    value
        .parse::<f64>()
        .map_err(|_| format!("invalid {name}: {value}"))
}

fn parse_tasks(value: &str) -> Vec<String> {
    value
        .split(',')
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(String::from)
        .collect()
}

fn parse_rules(value: &str) -> BTreeSet<String> {
    value
        .split(',')
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(String::from)
        .collect()
}

fn unixish_stamp() -> String {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
        .to_string()
}

fn help() -> String {
    "usage: bitgn-ecom-run run --env ecom|pac1|pac1-prod --tasks t01,t02 --run-id name --run-name leaderboard-name --leaderboard false --fail-fast false --workers 1 --rules catalog,inventory --max-wall-sum-seconds 156".to_string()
}
