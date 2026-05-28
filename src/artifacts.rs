use crate::config::RunConfig;
use crate::types::TaskResult;
use serde_json::json;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};

pub struct ArtifactWriter {
    run_dir: PathBuf,
}

impl ArtifactWriter {
    pub fn new(config: &RunConfig) -> Result<Self, String> {
        let run_dir = config.artifact_dir.join(&config.run_id);
        fs::create_dir_all(&run_dir).map_err(|e| e.to_string())?;
        let payload = json!({
            "run_id": config.run_id,
            "run_name": config.run_name,
            "env": config.env,
            "version": config.version,
            "leaderboard": config.leaderboard,
            "fail_fast": config.fail_fast,
            "workers": config.workers,
            "tasks": config.tasks,
            "enabled_rules": config.enabled_rules,
            "max_wall_sum_seconds": config.max_wall_sum_seconds,
        });
        write_json(&run_dir.join("run_config.json"), &payload)?;
        Ok(Self { run_dir })
    }

    pub fn append_task(&self, result: &TaskResult) -> Result<(), String> {
        append_jsonl(&self.run_dir.join("run_manifest.jsonl"), result)
    }

    pub fn finish(&self, results: &[TaskResult]) -> Result<(), String> {
        let passed = results.iter().filter(|r| r.passed == Some(true)).count();
        let failed = results
            .iter()
            .filter(|r| r.score_available && r.passed != Some(true))
            .count();
        let unscored = results.iter().filter(|r| !r.score_available).count();
        let wall_sum: f64 = results.iter().filter_map(|r| r.wall_seconds).sum();
        let payload = json!({
            "tasks_total": results.len(),
            "passed": passed,
            "failed": failed,
            "unscored": unscored,
            "pass_rate": if results.is_empty() { 0.0 } else { passed as f64 / results.len() as f64 },
            "task_wall_time_sum_seconds": wall_sum,
            "results": results,
        });
        write_json(&self.run_dir.join("run_summary.json"), &payload)
    }
}

pub fn write_json(path: &Path, payload: &serde_json::Value) -> Result<(), String> {
    let text = serde_json::to_string_pretty(payload).map_err(|e| e.to_string())?;
    fs::write(path, format!("{text}\n")).map_err(|e| e.to_string())
}

fn append_jsonl<T: serde::Serialize>(path: &Path, payload: &T) -> Result<(), String> {
    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
        .map_err(|e| e.to_string())?;
    let line = serde_json::to_string(payload).map_err(|e| e.to_string())?;
    writeln!(file, "{line}").map_err(|e| e.to_string())
}
