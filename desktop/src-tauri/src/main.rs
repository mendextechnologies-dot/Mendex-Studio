#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::{mpsc, Arc, Mutex};
use std::time::Duration;
use tauri::{Manager, State};

#[derive(Default)]
struct Bridge {
    child: Option<Child>,
    stdin: Option<ChildStdin>,
    responses: Option<mpsc::Receiver<String>>,
}

impl Bridge {
    fn stop(&mut self) {
        self.stdin.take();
        if let Some(mut child) = self.child.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
        self.responses.take();
    }

    fn start(&mut self, resources: &PathBuf) -> Result<(), String> {
        if let Some(child) = self.child.as_mut() {
            if child.try_wait().map_err(|e| e.to_string())?.is_none() {
                return Ok(());
            }
        }
        self.stop();
        let source = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
        let configured = std::env::var_os("MENDEX_PYTHON").map(PathBuf::from);
        let bundled = resources.join("backend/python.exe");
        let python = configured.or_else(|| bundled.is_file().then_some(bundled))
            .or_else(|| cfg!(debug_assertions).then(|| source.join(".venv/Scripts/python.exe")))
            .ok_or("Python backend unavailable. Install the backend and set MENDEX_PYTHON to its interpreter.")?;
        if !python.is_absolute() || !python.is_file() {
            return Err("MENDEX_PYTHON must identify an installed absolute Python interpreter".into());
        }
        let mut command = Command::new(python);
        command.args(["-u", "-m", "mendex_core.desktop"])
            .stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::inherit());
        if cfg!(debug_assertions) {
            command.current_dir(&source);
        } else {
            command.current_dir(resources);
        }
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            command.creation_flags(0x08000000);
        }
        let mut child = command.spawn().map_err(|e| format!("Backend startup failed: {e}"))?;
        self.stdin = child.stdin.take();
        let stdout = child.stdout.take().ok_or("Backend stdout unavailable")?;
        let (sender, receiver) = mpsc::channel();
        std::thread::spawn(move || {
            for line in BufReader::new(stdout).lines() {
                match line {
                    Ok(value) => if sender.send(value).is_err() { break; },
                    Err(_) => break,
                }
            }
        });
        self.child = Some(child);
        self.responses = Some(receiver);
        Ok(())
    }

    fn request(&mut self, request: &str, resources: &PathBuf) -> Result<String, String> {
        if request.len() > 256 * 1024 || request.contains('\n') || request.contains('\r') {
            return Err("Invalid or oversized desktop frame".into());
        }
        let value: serde_json::Value = serde_json::from_str(request).map_err(|e| e.to_string())?;
        let id = value.get("id").and_then(|v| v.as_str()).ok_or("Request ID required")?;
        self.start(resources)?;
        let exchange = (|| {
            let input = self.stdin.as_mut().ok_or("Backend stdin unavailable")?;
            writeln!(input, "{request}").map_err(|e| e.to_string())?;
            input.flush().map_err(|e| e.to_string())?;
            let line = self.responses.as_ref().ok_or("Backend reader unavailable")?
                .recv_timeout(Duration::from_secs(20)).map_err(|e| format!("Backend did not respond: {e}"))?;
            if line.len() > 8 * 1024 * 1024 { return Err("Backend response exceeds limit".into()); }
            let response: serde_json::Value = serde_json::from_str(&line).map_err(|e| e.to_string())?;
            if response.get("id").and_then(|v| v.as_str()) != Some(id) {
                return Err("Backend response identity mismatch".into());
            }
            Ok(line)
        })();
        if exchange.is_err() { self.stop(); }
        // An uncertain operation is never automatically replayed.
        exchange
    }
}

impl Drop for Bridge {
    fn drop(&mut self) { self.stop(); }
}

struct PythonBridge {
    bridge: Arc<Mutex<Bridge>>,
    resources: PathBuf,
}

#[tauri::command]
async fn rpc_dispatch(request: String, state: State<'_, PythonBridge>) -> Result<String, String> {
    let bridge = state.bridge.clone();
    let resources = state.resources.clone();
    tauri::async_runtime::spawn_blocking(move || {
        bridge.lock().map_err(|e| e.to_string())?.request(&request, &resources)
    }).await.map_err(|e| e.to_string())?
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            app.manage(PythonBridge { bridge: Arc::new(Mutex::new(Bridge::default())), resources: app.path().resource_dir()? });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![rpc_dispatch])
        .build(tauri::generate_context!())
        .expect("Failed to initialize Mendex desktop")
        .run(|app, event| {
            if matches!(event, tauri::RunEvent::Exit) {
                if let Ok(mut bridge) = app.state::<PythonBridge>().bridge.lock() { bridge.stop(); }
            }
        });
}
