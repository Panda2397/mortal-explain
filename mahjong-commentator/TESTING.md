# Development and testing

The commentator supports Python 3.12 through 3.14. Run commands from this
directory so its top-level `evaluator`, `parser`, and `llm` packages are on
the import path.

## Windows PowerShell

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

An existing virtual environment can be tested with only the final command.
`RiichiEnv` is not a Phase 1 dependency and must not be imported by the
commentator unless a completed-hand backend is selected later.
