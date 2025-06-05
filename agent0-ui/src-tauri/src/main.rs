// Tauri main application with system tray
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{CustomMenuItem, SystemTray, SystemTrayMenu, Manager, AppHandle, SystemTrayEvent};
use std::process::Command;

// Custom Tauri commands
#[tauri::command]
async fn pause_service() -> Result<String, String> {
    // Call Agent-0 pause endpoint
    let client = reqwest::Client::new();
    match client
        .post("http://localhost:8000/admin/pause")
        .send()
        .await
    {
        Ok(_) => Ok("Service paused".to_string()),
        Err(e) => Err(format!("Failed to pause service: {}", e)),
    }
}

#[tauri::command]
async fn resume_service() -> Result<String, String> {
    // Call Agent-0 resume endpoint
    let client = reqwest::Client::new();
    match client
        .post("http://localhost:8000/admin/resume")
        .send()
        .await
    {
        Ok(_) => Ok("Service resumed".to_string()),
        Err(e) => Err(format!("Failed to resume service: {}", e)),
    }
}

#[tauri::command]
async fn open_dashboard() -> Result<String, String> {
    // Open browser to monitoring dashboard
    if let Err(e) = webbrowser::open("http://localhost:8000/monitor") {
        Err(format!("Failed to open dashboard: {}", e))
    } else {
        Ok("Dashboard opened".to_string())
    }
}

fn create_system_tray() -> SystemTray {
    let pause = CustomMenuItem::new("pause".to_string(), "Pause Agent-0");
    let resume = CustomMenuItem::new("resume".to_string(), "Resume Agent-0");
    let dashboard = CustomMenuItem::new("dashboard".to_string(), "Open Dashboard");
    let separator = CustomMenuItem::new("separator".to_string(), "").disabled();
    let quit = CustomMenuItem::new("quit".to_string(), "Quit");

    let tray_menu = SystemTrayMenu::new()
        .add_item(pause)
        .add_item(resume)
        .add_item(separator)
        .add_item(dashboard)
        .add_item(separator)
        .add_item(quit);

    SystemTray::new().with_menu(tray_menu)
}

fn handle_system_tray_event(app: &AppHandle, event: SystemTrayEvent) {
    match event {
        SystemTrayEvent::LeftClick { .. } => {
            // Show main window on left click
            if let Some(window) = app.get_window("main") {
                window.show().unwrap();
                window.set_focus().unwrap();
            }
        }
        SystemTrayEvent::MenuItemClick { id, .. } => {
            match id.as_str() {
                "pause" => {
                    // Call pause command
                    tauri::async_runtime::spawn(async {
                        if let Err(e) = pause_service().await {
                            eprintln!("Failed to pause service: {}", e);
                        }
                    });
                }
                "resume" => {
                    // Call resume command
                    tauri::async_runtime::spawn(async {
                        if let Err(e) = resume_service().await {
                            eprintln!("Failed to resume service: {}", e);
                        }
                    });
                }
                "dashboard" => {
                    // Open dashboard
                    tauri::async_runtime::spawn(async {
                        if let Err(e) = open_dashboard().await {
                            eprintln!("Failed to open dashboard: {}", e);
                        }
                    });
                }
                "quit" => {
                    std::process::exit(0);
                }
                _ => {}
            }
        }
        _ => {}
    }
}

fn main() {
    tauri::Builder::default()
        .system_tray(create_system_tray())
        .on_system_tray_event(handle_system_tray_event)
        .invoke_handler(tauri::generate_handler![
            pause_service,
            resume_service,
            open_dashboard
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
} 