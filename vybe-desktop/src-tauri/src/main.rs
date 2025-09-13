#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{
    Manager, WindowEvent, State, GlobalShortcutManager
};
use std::sync::Mutex;
use std::process::{Command, Child};

// State to track if Python backend is running
struct BackendState {
    process: Mutex<Option<Child>>,
}

impl Drop for BackendState {
    fn drop(&mut self) {
        if let Some(mut process) = self.process.lock().unwrap().take() {
            println!("Shutting down Python backend...");
            let _ = process.kill();
            let _ = process.wait();
            println!("Python backend shut down.");
        }
    }
}

// Commands for frontend
#[tauri::command]
fn show_notification(app: tauri::AppHandle, title: String, body: String) {
    let _ = tauri::api::notification::Notification::new(&app.config().tauri.bundle.identifier)
        .title(&title)
        .body(&body)
        .show();
}

#[tauri::command]
fn get_system_info() -> serde_json::Value {
    serde_json::json!({
        "platform": std::env::consts::OS,
        "arch": std::env::consts::ARCH,
        "family": std::env::consts::FAMILY,
    })
}

#[tauri::command]
async fn check_backend_status() -> Result<bool, String> {
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build()
        .unwrap_or_default();
    
    // Try multiple health check endpoints
    let endpoints = vec![
        "http://127.0.0.1:8000/health",
        "http://127.0.0.1:8000/api/status",
        "http://127.0.0.1:8000/"
    ];
    
    for endpoint in endpoints {
        match client.get(endpoint).send().await {
            Ok(response) => {
                if response.status().is_success() {
                    println!("Backend health check passed at: {}", endpoint);
                    return Ok(true);
                }
            }
            Err(e) => {
                println!("Backend health check failed at {}: {}", endpoint, e);
            }
        }
    }
    
    Ok(false)
}

#[tauri::command]
fn shutdown_app(backend_state: State<BackendState>, app: tauri::AppHandle) {
    shutdown_backend(backend_state);
    app.exit(0);
}

#[tauri::command]
async fn get_backend_logs() -> String {
    // This could be expanded to read actual log files
    "Backend logs would be displayed here".to_string()
}

#[tauri::command] 
async fn restart_backend(backend_state: State<'_, BackendState>) -> Result<bool, String> {
    // Shutdown existing backend
    if let Some(mut process) = backend_state.process.lock().unwrap().take() {
        println!("Shutting down existing backend...");
        let _ = process.kill();
        let _ = process.wait();
    }
    
    // Wait a moment for cleanup
    tokio::time::sleep(std::time::Duration::from_secs(2)).await;
    
    // Start new backend
    let new_process = start_backend();
    *backend_state.process.lock().unwrap() = new_process;
    
    // Check if backend started successfully
    tokio::time::sleep(std::time::Duration::from_secs(5)).await;
    match check_backend_status().await {
        Ok(status) => Ok(status),
        Err(e) => Err(format!("Failed to check backend status: {}", e))
    }
}


// Start Python backend
fn start_backend() -> Option<Child> {
    // Get the current executable directory
    let exe_dir = match std::env::current_exe() {
        Ok(exe_path) => exe_path.parent().unwrap().to_path_buf(),
        Err(e) => {
            eprintln!("Failed to get executable directory: {}", e);
            return None;
        }
    };
    
    // Look for bundled vybe_app directory first
    let bundled_dir = exe_dir.join("vybe_app");
    
    // Try different Python setups with priority order for reliability
    let python_setups = if cfg!(target_os = "windows") {
        vec![
            // 1. Try bundled Python environment (for portable installation)
            (exe_dir.join("vybe-env-311-fixed").join("Scripts").join("python.exe"), exe_dir.clone()),
            // 2. Try development environment (if running from project directory)
            (std::env::current_dir().unwrap_or(exe_dir.clone()).join("vybe-env-311-fixed").join("Scripts").join("python.exe"), std::env::current_dir().unwrap_or(exe_dir.clone())),
            // 3. Try system Python with bundled app directory
            ("python.exe".to_string().into(), exe_dir.clone()),
            // 4. Try system Python in current directory (development mode)
            ("python.exe".to_string().into(), std::env::current_dir().unwrap_or(exe_dir.clone())),
        ]
    } else {
        vec![
            // Unix-like systems
            ("python3".to_string().into(), exe_dir.clone()),
            ("python3".to_string().into(), std::env::current_dir().unwrap_or(exe_dir.clone())),
        ]
    };
    
    for (python_cmd, working_dir) in python_setups {
        let python_str = python_cmd.to_string_lossy().to_string();
        let run_py_path = working_dir.join("run.py");
        
        // Check if run.py exists in this directory
        if !run_py_path.exists() {
            println!("run.py not found in {}, skipping...", working_dir.display());
            continue;
        }
        
        println!("Attempting to start Python backend...");
        println!("Python command: {}", python_str);
        println!("Working directory: {}", working_dir.display());
        println!("run.py path: {}", run_py_path.display());
        
        let backend_cmd = Command::new(&python_cmd)
            .arg("run.py")
            .current_dir(&working_dir)
            .env("VYBE_TEST_MODE", "true")  // Enable test mode for desktop app
            .env("VYBE_DESKTOP_MODE", "true")  // Indicate this is running from desktop app
            .spawn();
        
        match backend_cmd {
            Ok(child) => {
                println!("Python backend started successfully with PID: {}", child.id());
                return Some(child);
            }
            Err(e) => {
                eprintln!("Failed to start backend with {}: {}", python_str, e);
                continue;
            }
        }
    }
    
    eprintln!("All Python backend startup attempts failed!");
    eprintln!("Please ensure:");
    eprintln!("1. Python is installed and in PATH");
    eprintln!("2. Vybe application files are properly bundled");
    eprintln!("3. run.py exists in the application directory");
    None
}

// Shutdown Python backend
fn shutdown_backend(backend_state: State<BackendState>) {
    if let Some(mut process) = backend_state.process.lock().unwrap().take() {
        println!("Shutting down Python backend...");
        
        // Try graceful shutdown first
        if let Err(_) = process.try_wait() {
            // Process is still running, try to terminate gracefully
            #[cfg(target_os = "windows")]
            {
                use std::process::Command;
                // Send CTRL+C signal on Windows
                let _ = Command::new("taskkill")
                    .args(&["/F", "/T", "/PID", &process.id().to_string()])
                    .output();
            }
            
            #[cfg(not(target_os = "windows"))]
            {
                // Send SIGTERM on Unix-like systems
                let _ = process.kill();
            }
            
            // Wait up to 5 seconds for graceful shutdown
            let start = std::time::Instant::now();
            loop {
                if let Ok(Some(_)) = process.try_wait() {
                    println!("Python backend shut down gracefully");
                    break;
                }
                if start.elapsed().as_secs() > 5 {
                    println!("Forcing Python backend termination...");
                    let _ = process.kill();
                    let _ = process.wait();
                    break;
                }
                std::thread::sleep(std::time::Duration::from_millis(100));
            }
        }
        
        println!("Python backend shut down completed");
    }
}

fn main() {
    let backend_state = BackendState { process: Mutex::new(None) };

    tauri::Builder::default()
        .manage(backend_state)
        .invoke_handler(tauri::generate_handler![
            show_notification,
            get_system_info,
            check_backend_status,
            shutdown_app,
            get_backend_logs,
            restart_backend
        ])
        .setup(|app| {
            let backend_state = app.state::<BackendState>();
            *backend_state.process.lock().unwrap() = start_backend();

            let main_window = app.get_window("main").unwrap();

            let main_window_clone = main_window.clone();
            let app_handle = app.handle();
            main_window.on_window_event(move |event| {
                if let WindowEvent::CloseRequested { api, .. } = event {
                    api.prevent_close();
                    let backend_state = app_handle.state::<BackendState>();
                    shutdown_backend(backend_state);
                    let _ = main_window_clone.hide();
                }
            });

            let mut shortcut_manager = app.global_shortcut_manager();
            let app_handle = app.handle();

            let _ = shortcut_manager.register("CmdOrCtrl+Shift+V", move || {
                if let Some(window) = app_handle.get_window("main") {
                    if window.is_visible().unwrap_or(false) {
                        let _ = window.hide();
                    } else {
                        let _ = window.show();
                        let _ = window.set_focus();
                    }
                }
            });

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}