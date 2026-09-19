"""Entry point for the `agent` command.

`pyproject.toml` has declared `agent = "agent.cli:main"` since the package was
created, but this module did not exist — so `pip install -e .` produced an
`agent` command that failed on import. Created here rather than removing the
declaration, because a single named entry point is the right shape and the CLI
is a channel we want anyway.

Dispatch is a plain if/elif with the import INSIDE each branch. That keeps
`agent --help` fast as subcommands grow: starting the dashboard should not pay
to import a graph store client, and a missing optional dependency should only
break the subcommand that needs it.
"""

from __future__ import annotations

import sys

USAGE = """\
agent — Enterprise Agent Framework

  agent dashboard [--host HOST] [--port PORT]
        the local dashboard. Defaults to 127.0.0.1:7788.
        Overview renders the architecture from agent.dashboard.topology.

  agent --help
        this message
"""


def _flag(args: list[str], name: str, fallback: str) -> str:
    """Read `--name value`, returning fallback when absent.

    Unknown flags are left alone rather than rejected, so a subcommand can own
    its own arguments without this function needing to know them.
    """
    if name in args:
        index = args.index(name)
        if index + 1 < len(args):
            return args[index + 1]
        raise SystemExit(f"{name} needs a value")
    return fallback


def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "help"):
        print(USAGE)
        return

    command = args[0]

    if command == "dashboard":
        from agent.dashboard import DEFAULT_HOST, DEFAULT_PORT, serve

        host = _flag(args, "--host", DEFAULT_HOST)
        port_text = _flag(args, "--port", str(DEFAULT_PORT))
        try:
            port = int(port_text)
        except ValueError:
            raise SystemExit(f"--port must be a number, got {port_text!r}") from None
        serve(host=host, port=port)
        return

    print(f"unknown command {command!r}\n")
    print(USAGE)
    raise SystemExit(2)


if __name__ == "__main__":
    main()
