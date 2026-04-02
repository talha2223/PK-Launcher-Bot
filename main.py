import runpy
import pathlib
import sys

if __name__ == "__main__":
    root = pathlib.Path(__file__).resolve().parent
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "bot"))
    runpy.run_path(str(root / "bot" / "main.py"), run_name="__main__")
