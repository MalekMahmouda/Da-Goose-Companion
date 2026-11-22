# Da Goose Studio

A substantial local-first upgrade of **Da Goose Companion**, originally created by **Belal ElKhayat**. The original MIT license and attribution are retained in `LICENSE`. This branch adds a new, runnable app without replacing Belal's vector goose, skins, animations or playful interactions.

## Run it

Use Python **3.10 or newer** on a desktop computer. Windows is the primary target for the original floating companion. The productivity dashboard also runs with PyQt6 on Linux/macOS; desktop behavior varies by window manager.

```sh
git clone --branch feature/goose-studio --single-branch https://github.com/MalekMahmouda/Da-Goose-Companion.git
cd Da-Goose-Companion
python -m venv .venv
```

Activate the virtual environment:

- Windows PowerShell: `.venv\Scripts\Activate.ps1`
- macOS/Linux: `source .venv/bin/activate`

```sh
python -m pip install PyQt6 Pillow
python goose_studio.py
```

No API key, cloud account, paid service, compiler or installer is required for the local features. `requirements.txt` is inherited from the original and also includes optional development packages; the two packages above are enough for Studio.

To open only the dashboard, without the floating desktop goose:

```sh
python goose_studio.py --demo
```

`--demo` does **not** seed fake tasks or statistics. It simply skips launching the floating goose. Data is still saved normally. For a separate test profile:

```sh
python goose_studio.py --demo --data-dir ./my-test-profile
```

## What's new

### Focus nest

- Redesigned, resizable four-page desktop dashboard with a live vector goose preview.
- 15, 25 and 50 minute presets, plus custom focus durations from 1 to 180 minutes.
- Start, pause and resume with a monotonic countdown and visible progress.
- Link a focus session to an unfinished task.
- A completed focus session prepares a five-minute break. Breaks start only when you choose.
- A completed break prepares your next focus session, again without starting it automatically.
- Save or discard partial focus sessions when resetting or closing. Cancel keeps the timer intact.
- Offline goose pep talks, with no network request.

### Task pond

- Persistent task list backed by SQLite.
- Projects and High / Normal / Low priorities.
- Search by task or project, including finished tasks when requested.
- Complete, reopen, delete and focus on selected tasks.
- Deleting a task retains its focus-time history.

### Your rhythm

- Daily focus minutes and full-session totals.
- Seven-day focus chart with empty days included.
- A configurable daily goal and progress bar.
- Earned-feather milestones for starting, four weekly sessions, five finished tasks and reaching your daily goal.
- CSV export of session time, linked tasks and projects. Potential spreadsheet formula prefixes are neutralized.

### Feather controls

- All original goose skins remain available, with live preview.
- A quiet mode suppresses sounds, idle chatter and guard interruptions.
- Opt-in water reminders every 45 minutes and stretch reminders every 60 minutes.
- Original Windows title-based distraction guard is opt-in. It nudges rather than blocks applications.
- Manual, separately confirmed screen peeks. Automatic screenshot uploads are disabled in Studio.
- Keyboard shortcuts: Ctrl+1 focus, Ctrl+2 tasks, Ctrl+N new task, Ctrl+Space start/pause.

## Optional Gemini screen peek

Studio works fully without this feature. To use it, set `GEMINI_API_KEY` in **your own local environment** before launching. Do not put a real key in source files, Git commits or screenshots. Studio never writes this key to disk. The original configuration file may contain an older key if you previously used the upstream app; Studio does not read it for screen peeks or erase it.

The Controls page lets you enter a Gemini model ID available to your account. `GEMINI_MODEL` can set the initial model. The supplied default is a configurable identifier, not a promise that your account has access.

Each peek first asks for confirmation. Accepting it captures a JPEG thumbnail of the **entire primary screen** and sends it to **Google Gemini**. Close private documents and messages first. API usage may cost money under your Google account's terms. No screenshot is saved by Studio. Capturing happens on the GUI thread; the network request runs in a background worker. Returned text is displayed as plain text and never executed. Closing waits for an in-flight request to finish.

The implementation was tested for missing keys, cancelled consent, response parsing and network-error paths with mocked inputs. A real Gemini request has **not** been tested with a user's key or screen.

## Data and privacy

- Tasks, preferences and completed/explicitly saved partial sessions are stored locally in `studio.sqlite3` inside the existing companion configuration folder.
- The exact location is displayed on the Controls page.
- Studio does not store screenshots, active-window titles or API keys in its database.
- No analytics, account signup, automatic cloud sync or auto-updater is added.
- Reminders work only while the app is running. The focus timer measures running timer time, not attention or keyboard activity.
- Unsaved active time can be lost if the app or computer crashes. Normal closing offers to save partial time.
- Closing the dashboard exits the app and stops the companion. The original tray menu can show/hide the floating goose and open Studio controls.

Back up the data by closing Studio and copying the configuration folder. Restore that folder while Studio is closed.

## Tests

```sh
python -m unittest test_studio -v
```

For headless Linux:

```sh
QT_QPA_PLATFORM=offscreen python -m unittest test_studio -v
```

The tests cover countdown accuracy, pause/resume, one-time completion, break handling, storage, searching, priority order, completed tasks, history retention, export safety, all four pages, all skins, privacy refusal, reminders and companion shutdown.

Verification was performed with Python 3.10 and PyQt6 on Linux using Qt's offscreen renderer. Screenshots are actual application renders with clearly disposable example tasks/statistics. Native Windows tray integration, real Windows foreground-window detection and macOS window behavior still need on-device testing. Native Linux Qt may require your distribution's Qt/XCB packages, including `libxcb-cursor0`; a headless render does not validate a complete desktop installation.

## Files and license

- `goose_studio.py`: new entry point, local storage, timer, dashboard and safer manual screen-peek path.
- `test_studio.py`: regression tests.
- Other Python modules and artwork: original companion, kept intact.
- `LICENSE`: original MIT license, unchanged.

This is a feature branch on a fork. It does not change the upstream repository, create a pull request or publish an executable release.
