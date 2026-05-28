use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskResult {
    pub task_id: String,
    pub trial_id: Option<String>,
    #[serde(default)]
    pub score_available: bool,
    pub passed: Option<bool>,
    pub score: Option<f64>,
    pub solver: String,
    pub workspace: PathBuf,
    pub error: Option<String>,
    pub score_detail: Vec<String>,
    pub wall_seconds: Option<f64>,
}
