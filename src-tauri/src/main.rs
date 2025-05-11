#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    sync::{Arc, Mutex},
    thread,
    time::Duration,
};

use arboard::Clipboard;
use chrono::Utc;
use rusqlite::{params, Connection};
use tauri::{
    menu::{MenuBuilder, MenuItemBuilder},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Emitter, Manager, Runtime,
};

// ---------- helper ----------------------------------------------------------

fn app_data_dir<R: Runtime>(app: &AppHandle<R>) -> std::path::PathBuf {
    app.path()
        .app_data_dir()
        .expect("cannot determine app-data dir")
}

// ---------- tauri commands --------------------------------------------------

#[tauri::command]
fn get_history(
    db_state: tauri::State<'_, Arc<Mutex<Connection>>>,
) -> Result<Vec<String>, String> {
    let rows = {
        let db   = db_state.lock().map_err(|e| e.to_string())?;
        let mut stmt = db
            .prepare("SELECT text FROM clip ORDER BY ts DESC LIMIT 20")
            .map_err(|e| e.to_string())?;

        let iter = stmt
            .query_map([], |row| row.get::<_, String>(0))
            .map_err(|e| e.to_string())?;

        iter.filter_map(Result::ok).collect::<Vec<_>>()
    };
    Ok(rows)
}

#[tauri::command]
fn copy_to_clipboard(text: String) -> Result<(), String> {
    Clipboard::new()
        .map_err(|e| e.to_string())?
        .set_text(text)
        .map_err(|e| e.to_string())
}

// ---------- main ------------------------------------------------------------

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            // 1.  SQLite ------------------------------------------------------
            let data_dir = app_data_dir(&app.app_handle());
            std::fs::create_dir_all(&data_dir)?;
            let conn = Connection::open(data_dir.join("history.db"))?;
            conn.execute(
                "CREATE TABLE IF NOT EXISTS clip (ts REAL PRIMARY KEY, text TEXT)",
                [],
            )?;
            let db = Arc::new(Mutex::new(conn));
            app.manage(db.clone());

            // 2.  clipboard poller ('static) ----------------------------------
            let app_handle: AppHandle<_> = app.app_handle().clone(); // ← `'static`
            let db_clone = db.clone();                       // ← Arc => `'static`
            thread::spawn(move || {
                let mut cb   = Clipboard::new().expect("clipboard");
                let mut last = String::new();

                loop {
                    if let Ok(txt) = cb.get_text() {
                        if !txt.is_empty() && txt != last {
                            last = txt.clone();

                            // write to DB
                            let ts = Utc::now().timestamp_millis();
                            let _ = db_clone
                                .lock()
                                .unwrap()
                                .execute("INSERT INTO clip VALUES (?,?)", params![ts, txt]);

                            // notify front-end
                            let _ = app_handle.emit("clipboard-changed", &last);
                        }
                    }
                    thread::sleep(Duration::from_millis(400));
                }
            });

            // 3.  tray icon + menu -------------------------------------------
            let show = MenuItemBuilder::with_id("show", "Show history…").build(app)?;
            let quit = MenuItemBuilder::with_id("quit", "Exit").build(app)?;
            let menu = MenuBuilder::new(app).items(&[&show, &quit]).build()?;
            let icon = app.default_window_icon().ok_or("no default icon")?.clone();

            TrayIconBuilder::with_id("tray")
                .icon(icon)
                .menu(&menu)
                .on_menu_event(|app, ev| match ev.id().as_ref() {
                    "show" => {
                        if let Some(w) = app.get_webview_window("main") {
                            let _ = w.show();
                            let _ = w.set_focus();
                        }
                    }
                    "quit" => std::process::exit(0),
                    _ => {}
                })
                .on_tray_icon_event(|tray, ev| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = ev
                    {
                        if let Some(w) = tray.app_handle().get_webview_window("main") {
                            let _ = w.show();
                            let _ = w.set_focus();
                        }
                    }
                })
                .build(app)?;

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![get_history, copy_to_clipboard])
        .run(tauri::generate_context!())
        .expect("error while running tauri app");
}
