use crate::artifacts::ArtifactWriter;
use crate::bridge::Bridge;
use crate::config::RunConfig;
use crate::types::TaskResult;
use std::collections::{BTreeMap, VecDeque};
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;

pub fn run(config: RunConfig) -> Result<(), String> {
    let writer = ArtifactWriter::new(&config)?;
    let bridge = Bridge::discover();
    let leaderboard = if config.leaderboard {
        Some(prepare_leaderboard(&config, &bridge)?)
    } else {
        None
    };
    let seeds = leaderboard
        .as_ref()
        .map(|prep| Arc::new(prep.seeds.clone()));
    let results = if config.workers <= 1 {
        run_sequential(&config, &bridge, &writer, seeds.clone())?
    } else {
        run_parallel(&config, &bridge, &writer, seeds.clone())?
    };
    writer.finish(&results)?;
    if let Some(prep) = leaderboard {
        submit_if_eligible(&config, &bridge, &results, &prep.run_id)?;
    }
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

fn submit_if_eligible(
    config: &RunConfig,
    bridge: &Bridge,
    results: &[TaskResult],
    leaderboard_run_id: &str,
) -> Result<(), String> {
    let all_tasks_completed = results.len() == config.tasks.len();
    let all_passed = all_tasks_completed && results.iter().all(|r| r.passed);
    let all_timed = results.iter().all(|r| r.wall_seconds.is_some());
    let wall_sum: f64 = results.iter().filter_map(|r| r.wall_seconds).sum();
    let wall_ok = config
        .max_wall_sum_seconds
        .map(|limit| wall_sum < limit)
        .unwrap_or(true);
    if all_passed && all_timed && wall_ok {
        bridge.submit_leaderboard(leaderboard_run_id)?;
        return Ok(());
    }
    Err(format!(
        "leaderboard submit skipped: passed={}/{} wall_sum_seconds={:.3} limit={:?}",
        results.iter().filter(|r| r.passed).count(),
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
        let failed = !result.passed;
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
            if config.fail_fast && !result.passed {
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
    match try_run_one(config, bridge, task_id, seeds) {
        Ok(result) => result,
        Err((workspace, error)) => TaskResult {
            task_id: task_id.into(),
            passed: false,
            score: 0.0,
            solver: "error".into(),
            workspace,
            error: Some(error),
            score_detail: Vec::new(),
            wall_seconds: None,
        },
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
