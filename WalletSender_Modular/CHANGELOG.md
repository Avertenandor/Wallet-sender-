# Changelog

## v2.1.0 (2025-08-31)

Improvements:

- UI: Dark theme enabled by default (qdarkstyle + Fusion).
- PyQt compatibility: safe fallbacks for QFont weight, Qt.Alignment and QSplitter orientation (PyQt5/6).
- Analysis: slot signature aligned with signal to avoid runtime errors.
- Rewards: added `_update_rewards_table` slot to reflect changes in UI.
- History: restored `log_message` via BaseTab for backward compatibility; tab loads reliably.

Notes:

- Minor warnings from third-party packages (setuptools/pkg_resources) do not affect functionality.
- Further polishing planned for HistoryTab status bar messages and actions.
