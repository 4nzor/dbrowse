# Contributing to dbrowse

Thank you for your interest in contributing to dbrowse! This document provides guidelines and instructions for contributing.

## Getting Started

1. Fork the repository on GitLab
2. Clone your fork: `git clone https://gitlab.com/yourusername/dbrowse.git`
3. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

## Development Workflow

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bugfix-name
   ```

2. Make your changes and test them thoroughly

3. Ensure your code follows the existing style:
   - Use type hints where appropriate
   - Follow PEP 8 style guidelines
   - Add docstrings for new functions/classes

4. Commit your changes with clear, descriptive messages:
   ```bash
   git commit -m "Add feature: description of what you did"
   ```

5. Push to your fork and create a Merge Request on GitLab

## Code Style

- Follow PEP 8 Python style guide
- Use type hints for function parameters and return types
- Keep functions focused and small
- Add docstrings for public functions and classes
- Use meaningful variable and function names

## Testing

Before submitting a merge request, please:

1. Test your changes with different database types (PostgreSQL, MySQL, SQLite, MongoDB, ClickHouse)
2. Test edge cases (empty tables, large datasets, connection errors)
3. Ensure the UI remains responsive and doesn't crash

## Reporting Issues

When reporting bugs, please include:

- Description of the issue
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details (OS, Python version, database type and version)
- Error messages or screenshots if applicable

## Feature Requests

For feature requests, please:

- Describe the feature clearly
- Explain the use case
- Consider if it fits with the project's goals
- Be open to discussion and feedback

## Database Adapter Development

If you're adding support for a new database type:

1. Create a new adapter class in `database.py` that inherits from `DatabaseAdapter`
2. Implement all required abstract methods
3. Add the adapter to the `get_adapter()` function
4. Update the README with connection string format
5. Test thoroughly with real database instances

## Questions?

If you have questions about contributing, feel free to open an issue or contact the maintainers.

Thank you for contributing to dbrowse! 🎉

