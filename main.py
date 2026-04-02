# main.py
"""
Entrypoint for the Anansi project.
For running UI.
"""
from anansi.ui.app import st

if __name__ == "__main__":
    # Launch Streamlit app
    import subprocess
    subprocess.run(["streamlit", "run", "src/anansi/ui/app.py"])