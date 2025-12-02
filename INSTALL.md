# Installation Guide

## Install as Command (Recommended)

After installation, you can run `dbrowse` or `dbrowser` from anywhere in your terminal.

### Development Installation

```bash
# Using Makefile (recommended)
make install-package

# Or manually
pip install -e .
```

### Production Installation

```bash
# From local directory
pip install .

# Or from Git repository
pip install git+https://github.com/4nzor/dbrowse.git
```

### Verify Installation

```bash
# Check if command is available
which dbrowse
which dbrowser

# Run the application
dbrowse
# or
dbrowser
```

## Uninstall

```bash
pip uninstall dbrowse
```

## Troubleshooting

### Command not found after installation

1. Make sure your Python bin directory is in PATH:
   ```bash
   # Check Python bin location
   python -m site --user-base
   
   # Add to PATH (add to ~/.bashrc or ~/.zshrc)
   export PATH="$HOME/.local/bin:$PATH"
   ```

2. Or use virtual environment:
   ```bash
   source venv/bin/activate
   make install-package
   ```

### Permission denied

If you get permission errors, use `--user` flag:
```bash
pip install --user -e .
```

