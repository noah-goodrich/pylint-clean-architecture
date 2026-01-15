"""
Stellar Engineering Command: User Interface
Handles CLI output, branding, and status messages.
"""

import os
import sys

from clean_architecture_linter.constants import EXCELSIOR_BANNER


class SystemUI:
    """Handles visual telemetry and system announcements."""

    @staticmethod
    def announce_initialization():
        """
        Prints the Excelsior status.
        - Banner: If Interactive TTY and Color enabled.
        - Colored Text: If Non-Interactive but Color enabled (CI/Logs).
        - Plain Text: If Color disabled (NO_COLOR) or fallback.
        - Silent: If quiet flags are set.
        """
        # 1. Check Silence
        if any(arg in sys.argv for arg in ["-q", "--quiet", "--silent"]):
            return

        # 2. Check Color Capability
        use_color = not os.getenv("NO_COLOR")

        # 3. Determine Output
        # JUSTIFICATION: TTY checks require standard library delegation
        if sys.stdout.isatty() and use_color:  # pylint: disable=clean-arch-delegation,clean-arch-demeter
            print(EXCELSIOR_BANNER)
        elif use_color:
            # User requested colored text instead of emoji icon
            print("\033[31m[EXCELSIOR]\033[0m Initializing architectural integrity scan...")
        else:
            print("[EXCELSIOR] Initializing architectural integrity scan...")
