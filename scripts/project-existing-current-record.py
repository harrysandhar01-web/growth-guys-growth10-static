"""Project the accepted current record; never collect or approve evidence.

Existing protected publishers invoke this entrypoint without arguments.
An optional public-directory argument is supported for isolated fixture tests.
"""
from pathlib import Path
import runpy

if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).with_name('project-current-checkout-copy.py')), run_name='__main__')
