"""
# Docstring: A module-level string that explains what the file does.
# It helps readers, IDEs, and tooling quickly understand purpose/usage.

Friendly alias for the pipeline runner. This simply calls the
implementation1 main(), keeping a nicer command name:

    python -m scripts.run_pipeline --mode quick
    python -m scripts.run_pipeline --mode postgis --include-esri
"""

from __future__ import annotations

from scripts.implementation1 import main


if __name__ == "__main__":
    main()

