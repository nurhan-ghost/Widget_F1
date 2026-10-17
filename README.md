# F1 Standings

A compact Windows desktop widget built with Python and PySide6. English interface,
three-letter driver codes, team accents, and exactly six visible rows. Scroll to
see the rest of the grid without resizing the window.

## Run in VS Code

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m f1widget
```

Open this folder in VS Code and select **F1 Widget** in Run and Debug (F5).
The Microsoft Python and Python Debugger extensions are required for F5.

Drag the title area to move the window. **PIN** keeps it above other windows.
**×** hides it to the system tray; use the tray menu to show it or quit.
The window position and pin preference are remembered. Autostart is not enabled.

## Data

[Jolpica F1](https://github.com/jolpica/jolpica-f1/tree/main/docs) supplies driver
and constructor standings. Data is cached in the Windows application-data folder
and refreshed daily while the app runs (checked hourly), or manually with ↻.
The saved timestamp is always visible. If the network fails, saved standings
remain available and are marked offline. On first launch without internet, an
empty state is shown; no fabricated standings are used.

Gaps are measured against the leader. Position movement compares the current
round with the previous round in the same season, not the previous refresh.
Unavailable previous-round data is shown as a dash. Team colors are display
accents and can be adjusted in `theme.py`.

## Structure

- `src/f1widget/models.py`: standings parsing, position movement, points gaps.
- `src/f1widget/service.py`: HTTP requests and atomic disk cache.
- `src/f1widget/window.py`: desktop window, worker lifecycle, tray, rows.
- `src/f1widget/theme.py`: style and team accents.
- `tests/`: calculation, cache and offscreen UI checks.

## Branch workflow

Use `feat/<feature>`, `fix/<issue>`, or `chore/<maintenance>` branches.
Keep commits focused with matching `feat:`, `fix:`, or `chore:` messages.
Push the named branch and review it before merging to `main`. Never push feature
work directly to `main`. Initial implementation: `feat/python-desktop-widget`.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
