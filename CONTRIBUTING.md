# Contributing to Visa Requirements Dataset

Thank you for your interest in contributing!

## License

By contributing to this project, you agree that your code contributions will be licensed under the MIT License. Data corrections should be made on Wikipedia first, as this repository mirrors Wikipedia content (licensed under CC BY-SA 4.0).

## Data Corrections

**Important:** This dataset is automatically generated from Wikipedia. If you notice incorrect visa data:

1. **First, check the Wikipedia article**: Most data issues originate from the source Wikipedia article
2. **Edit Wikipedia directly**: Make corrections on the relevant "Visa requirements for X citizens" article on English Wikipedia
3. **Wait for the next update**: The pipeline runs weekly and will pick up your changes

Only open an issue here if:
- The Wikipedia article is correct but the pipeline is parsing it incorrectly
- You've found a systematic parsing or mapping issue

## Code Contributions

### Getting Started

1. Fork the repository
2. Create a virtual environment: `python3 -m venv .venv`
3. Install dependencies: `.venv/bin/pip install -e ".[dev]"`
4. Create a branch for your changes: `git checkout -b feature/my-contribution`

### Running Tests

```bash
.venv/bin/pytest -q
```

### Linting

```bash
.venv/bin/python -m pyflakes src tests
```

### Making Changes

1. Write tests for your changes
2. Ensure all tests pass
3. Follow the existing code style
4. Sign your commits: `git commit -s`
5. Open a pull request with a clear description

### Commit Messages

- Use clear, descriptive commit messages
- Sign your commits with `git commit -s` (Developer Certificate of Origin)

## Questions?

Open an issue for questions about contributing or the project architecture.
