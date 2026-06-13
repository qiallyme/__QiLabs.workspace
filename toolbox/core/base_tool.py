# core/base_tool.py

class BaseTool:
    def reset_run_state(self):
        """Reset lightweight outcome metadata before each execution."""
        self._run_status = "success"
        self._run_message = ""

    def set_run_status(self, status, message=""):
        """Record a normalized run outcome for the shell."""
        self._run_status = status
        self._run_message = message

    def get_run_status(self):
        """Return the normalized run outcome tuple."""
        return getattr(self, "_run_status", "success"), getattr(self, "_run_message", "")

    def get_name(self):
        """The name that appears in the sidebar."""
        raise NotImplementedError

    def build_ui(self, parent_frame):
        """Build the specific input fields for this tool."""
        raise NotImplementedError

    def execute(self, target_path, is_dry_run, log_callback, progress_callback):
        """The actual logic of the tool."""
        raise NotImplementedError
