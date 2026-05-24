use crate::types::TaskResult;
use serde_json::Value;
use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Debug, Clone)]
pub struct Bridge {
    script: PathBuf,
}

impl Bridge {
    pub fn discover() -> Self {
        Self {
            script: PathBuf::from("tools/bitgn_bridge.py"),
        }
    }

    pub fn prepare_leaderboard(
        &self,
        env: &str,
        task_ids: &[String],
        run_name: &str,
    ) -> Result<Value, String> {
        let mut args = self.base_args();
        args.extend([
            "prepare-leaderboard".into(),
            "--env".into(),
            env.into(),
            "--tasks".into(),
            task_ids.join(","),
            "--run-name".into(),
            run_name.into(),
        ]);
        self.run_json(args)
    }

    pub fn submit_leaderboard(&self, run_id: &str) -> Result<Value, String> {
        let mut args = self.base_args();
        args.extend([
            "submit-leaderboard".into(),
            "--run-id".into(),
            run_id.into(),
        ]);
        self.run_json(args)
    }

    pub fn run_task(
        &self,
        env: &str,
        task_id: &str,
        run_id: &str,
        artifact_dir: &Path,
        leaderboard: bool,
        trial_seed_json: Option<&str>,
    ) -> Result<TaskResult, String> {
        let mut args = self.base_args();
        args.extend([
            "run-task".into(),
            "--env".into(),
            env.into(),
            "--task-id".into(),
            task_id.into(),
            "--run-id".into(),
            run_id.into(),
        ]);
        args.extend(["--artifact-dir".into(), artifact_dir.display().to_string()]);
        if leaderboard {
            args.push("--leaderboard".into());
        }
        if let Some(seed) = trial_seed_json {
            args.extend(["--trial-seed".into(), seed.into()]);
        }
        let value = self.run_json(args)?;
        serde_json::from_value(value).map_err(|e| format!("run-task decode error: {e}"))
    }

    fn base_args(&self) -> Vec<String> {
        vec![
            "run".into(),
            "python".into(),
            self.script.display().to_string(),
        ]
    }

    fn run_json(&self, args: Vec<String>) -> Result<Value, String> {
        let out = Command::new("uv")
            .args(args)
            .output()
            .map_err(|e| e.to_string())?;
        if !out.status.success() {
            return Err(String::from_utf8_lossy(&out.stderr).to_string());
        }
        let stdout = String::from_utf8_lossy(&out.stdout);
        let line = stdout
            .lines()
            .rev()
            .find(|line| line.trim_start().starts_with('{'))
            .ok_or_else(|| stdout.to_string())?;
        serde_json::from_str(line).map_err(|e| format!("bridge json error: {e}: {line}"))
    }
}
