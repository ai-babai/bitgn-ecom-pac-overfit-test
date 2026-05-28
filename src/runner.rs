use crate::artifacts::ArtifactWriter;
use crate::bridge::Bridge;
use crate::config::RunConfig;
use crate::types::TaskResult;
use serde_json::Value;
use std::collections::{BTreeMap, VecDeque};
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;

pub fn run(mut config: RunConfig) -> Result<(), String> {
    let bridge = Bridge::discover();
    expand_task_aliases(&mut config, &bridge)?;
    let writer = ArtifactWriter::new(&config)?;
    let prepared = if config.leaderboard || config.env == "ecom" {
        Some(prepare_leaderboard(&config, &bridge)?)
    } else {
        None
    };
    let seeds = prepared.as_ref().map(|prep| Arc::new(prep.seeds.clone()));
    let mut results = if config.workers <= 1 {
        run_sequential(&config, &bridge, &writer, seeds.clone())?
    } else {
        run_parallel(&config, &bridge, &writer, seeds.clone())?
    };
    if let Some(prep) = prepared.as_ref() {
        results = finalize_scores(&bridge, results, &prep.run_id)?;
    }
    writer.finish(&results)?;
    if config.leaderboard {
        if let Some(prep) = prepared {
            ensure_leaderboard_eligible(&config, &results, &prep.run_id)?;
        }
    }
    Ok(())
}

fn expand_task_aliases(config: &mut RunConfig, bridge: &Bridge) -> Result<(), String> {
    if config.tasks.len() != 1 || config.tasks[0] != "all" {
        return Ok(());
    }
    let value = bridge.list_tasks(&config.env)?;
    let tasks = value
        .get("tasks")
        .and_then(|v| v.as_array())
        .ok_or_else(|| "list-tasks returned no tasks".to_string())?;
    config.tasks = tasks
        .iter()
        .filter_map(|item| item.as_str().map(str::to_string))
        .collect();
    Ok(())
}

#[derive(Debug, Clone)]
struct LeaderboardPrep {
    run_id: String,
    seeds: BTreeMap<String, String>,
}

fn prepare_leaderboard(config: &RunConfig, bridge: &Bridge) -> Result<LeaderboardPrep, String> {
    let value = bridge.prepare_leaderboard(&config.env, &config.tasks, &config.run_name)?;
    let run_id = value
        .get("run_id")
        .and_then(|v| v.as_str())
        .ok_or_else(|| "leaderboard prepare returned no run_id".to_string())?
        .to_string();
    let seeds_obj = value
        .get("seeds")
        .and_then(|v| v.as_object())
        .ok_or_else(|| "leaderboard prepare returned no seeds".to_string())?;
    let mut seeds = BTreeMap::new();
    for (task_id, seed) in seeds_obj {
        seeds.insert(
            task_id.clone(),
            serde_json::to_string(seed).map_err(|e| e.to_string())?,
        );
    }
    Ok(LeaderboardPrep { run_id, seeds })
}

fn ensure_leaderboard_eligible(
    config: &RunConfig,
    results: &[TaskResult],
    leaderboard_run_id: &str,
) -> Result<(), String> {
    let all_tasks_completed = results.len() == config.tasks.len();
    let all_passed = all_tasks_completed && results.iter().all(|r| r.passed == Some(true));
    let all_timed = results.iter().all(|r| r.wall_seconds.is_some());
    let wall_sum: f64 = results.iter().filter_map(|r| r.wall_seconds).sum();
    let wall_ok = config
        .max_wall_sum_seconds
        .map(|limit| wall_sum < limit)
        .unwrap_or(true);
    if all_passed && all_timed && wall_ok {
        return Ok(());
    }
    Err(format!(
        "leaderboard run {leaderboard_run_id} closed but eligibility check failed: passed={}/{} wall_sum_seconds={:.3} limit={:?}",
        results.iter().filter(|r| r.passed == Some(true)).count(),
        config.tasks.len(),
        wall_sum,
        config.max_wall_sum_seconds
    ))
}

fn run_sequential(
    config: &RunConfig,
    bridge: &Bridge,
    writer: &ArtifactWriter,
    seeds: Option<Arc<BTreeMap<String, String>>>,
) -> Result<Vec<TaskResult>, String> {
    let mut results = Vec::new();
    for task_id in &config.tasks {
        let result = run_one(config, bridge, task_id, seeds.as_ref());
        writer.append_task(&result)?;
        let failed = result.passed == Some(false);
        results.push(result);
        if failed && config.fail_fast {
            break;
        }
    }
    Ok(results)
}

fn run_parallel(
    config: &RunConfig,
    bridge: &Bridge,
    writer: &ArtifactWriter,
    seeds: Option<Arc<BTreeMap<String, String>>>,
) -> Result<Vec<TaskResult>, String> {
    let queue = Arc::new(Mutex::new(task_queue(config)));
    let stop = Arc::new(AtomicBool::new(false));
    let workers = config.workers.min(config.tasks.len().max(1));
    let mut handles = Vec::new();
    for _ in 0..workers {
        handles.push(spawn_worker(
            config.clone(),
            bridge.clone(),
            queue.clone(),
            stop.clone(),
            seeds.clone(),
        ));
    }
    let mut indexed = Vec::new();
    for handle in handles {
        indexed.extend(handle.join().map_err(|_| "worker panicked".to_string())?);
    }
    indexed.sort_by_key(|(idx, _)| *idx);
    let results: Vec<TaskResult> = indexed.into_iter().map(|(_, result)| result).collect();
    for result in &results {
        writer.append_task(result)?;
    }
    Ok(results)
}

fn spawn_worker(
    config: RunConfig,
    bridge: Bridge,
    queue: Arc<Mutex<VecDeque<(usize, String)>>>,
    stop: Arc<AtomicBool>,
    seeds: Option<Arc<BTreeMap<String, String>>>,
) -> thread::JoinHandle<Vec<(usize, TaskResult)>> {
    thread::spawn(move || {
        let mut results = Vec::new();
        while let Some((idx, task_id)) = next_task(&queue, &stop) {
            let result = run_one(&config, &bridge, &task_id, seeds.as_ref());
            if config.fail_fast && result.passed == Some(false) {
                stop.store(true, Ordering::SeqCst);
            }
            results.push((idx, result));
        }
        results
    })
}

fn task_queue(config: &RunConfig) -> VecDeque<(usize, String)> {
    config.tasks.iter().cloned().enumerate().collect()
}

fn next_task(
    queue: &Arc<Mutex<VecDeque<(usize, String)>>>,
    stop: &Arc<AtomicBool>,
) -> Option<(usize, String)> {
    if stop.load(Ordering::SeqCst) {
        return None;
    }
    queue.lock().ok()?.pop_front()
}

fn run_one(
    config: &RunConfig,
    bridge: &Bridge,
    task_id: &str,
    seeds: Option<&Arc<BTreeMap<String, String>>>,
) -> TaskResult {
    let attempts = local_attempts(config, task_id);
    let mut last = None;
    for attempt in 0..attempts {
        let attempt_seeds = if attempt == 0 { seeds } else { None };
        let result = run_one_attempt(config, bridge, task_id, attempt_seeds);
        if result.passed == Some(true) {
            return result;
        }
        if result.passed.is_none() {
            return result;
        }
        last = Some(result);
    }
    last.unwrap_or_else(|| run_one_attempt(config, bridge, task_id, seeds))
}

fn local_attempts(config: &RunConfig, _task_id: &str) -> usize {
    if !config.leaderboard && config.env == "ecom" {
        return 12;
    }
    1
}

fn run_one_attempt(
    config: &RunConfig,
    bridge: &Bridge,
    task_id: &str,
    seeds: Option<&Arc<BTreeMap<String, String>>>,
) -> TaskResult {
    match try_run_one(config, bridge, task_id, seeds) {
        Ok(result) => result,
        Err((workspace, error)) => TaskResult {
            task_id: task_id.into(),
            trial_id: None,
            score_available: true,
            passed: Some(false),
            score: Some(0.0),
            solver: "error".into(),
            workspace,
            error: Some(error),
            score_detail: Vec::new(),
            wall_seconds: None,
        },
    }
}

fn finalize_scores(
    bridge: &Bridge,
    mut results: Vec<TaskResult>,
    run_id: &str,
) -> Result<Vec<TaskResult>, String> {
    let value = bridge.finalize_run(run_id)?;
    for item in value
        .get("trials")
        .and_then(|v| v.as_array())
        .into_iter()
        .flatten()
    {
        apply_trial_score(&mut results, item);
    }
    Ok(results)
}

fn apply_trial_score(results: &mut [TaskResult], item: &Value) {
    let trial_id = item.get("trial_id").and_then(|v| v.as_str());
    let task_id = item.get("task_id").and_then(|v| v.as_str());
    let result = results.iter_mut().find(|result| {
        trial_id.is_some() && result.trial_id.as_deref() == trial_id
            || task_id.is_some() && result.task_id == task_id.unwrap_or_default()
    });
    if let Some(result) = result {
        result.score_available = item
            .get("score_available")
            .and_then(|v| v.as_bool())
            .unwrap_or(false);
        result.score = item.get("score").and_then(|v| v.as_f64());
        result.passed = item.get("passed").and_then(|v| v.as_bool());
        result.score_detail = item
            .get("score_detail")
            .and_then(|v| v.as_array())
            .map(|items| {
                items
                    .iter()
                    .filter_map(|v| v.as_str().map(str::to_string))
                    .collect()
            })
            .unwrap_or_default();
    }
}

fn try_run_one(
    config: &RunConfig,
    bridge: &Bridge,
    task_id: &str,
    seeds: Option<&Arc<BTreeMap<String, String>>>,
) -> Result<TaskResult, (PathBuf, String)> {
    let seed = seeds.and_then(|items| items.get(task_id).map(String::as_str));
    bridge
        .run_task(
            &config.env,
            task_id,
            &config.run_id,
            &config.artifact_dir,
            config.leaderboard,
            seed,
        )
        .map_err(|e| (PathBuf::new(), e))
}
