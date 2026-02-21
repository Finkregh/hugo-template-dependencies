"""Nox configuration for hugo-template-dependencies."""

import nox

nox.options.sessions = ["lint", "test", "type_check"]
nox.options.default_venv_backend = "uv"


@nox.session
def lint(session: nox.Session) -> None:
    """Run code formatting and linting checks."""
    session.run("uv", "sync")
    session.run("uv", "run", "ruff", "check", ".")
    session.run("uv", "run", "ruff", "format", ".")
    session.run("uv", "run", "pre-commit", "run", "-a")
    session.run("uv", "run", "deptry", "src")


@nox.session(python=["3.10", "3.11", "3.12", "3.13", "3.14"])
def test(session: nox.Session) -> None:
    """Run tests with coverage."""
    session.run("uv", "sync", "--python", str(session.python))
    session.run(
        "uv",
        "run",
        "python",
        "-m",
        "pytest",
        "--doctest-modules",
        "tests",
        "--cov",
        "--cov-config=pyproject.toml",
        "--cov-report=xml",
    )


def test(session: nox.Session) -> None:
    """Run tests with coverage."""
    session.run("uv", "sync", "--python", session.python)
    session.run(
        "uv",
        "run",
        "python",
        "-m",
        "pytest",
        "--doctest-modules",
        "tests",
        "--cov",
        "--cov-config=pyproject.toml",
        "--cov-report=xml",
    )


@nox.session
def type_check(session: nox.Session) -> None:
    """Run type checking."""
    session.run("uv", "sync")
    session.run("uv", "run", "ty", "check")


@nox.session
def docs(session: nox.Session) -> None:
    """Build documentation."""
    session.run("uv", "sync")
    session.run("uv", "run", "mkdocs", "build", "-s")


@nox.session
def docs_serve(session: nox.Session) -> None:
    """Serve documentation locally."""
    session.run("uv", "sync")
    session.run("uv", "run", "mkdocs", "serve")
