"""
Agent storage backends — BackendProtocol implementations.

deepagents routes filesystem tool calls (read_file, write_file, ls, grep, glob)
through the backend layer. Each backend is plugged into a CompositeBackend in
brain.py which routes calls to the right backend by path prefix:
  /workspace  → S3Backend (persistent, eu-west-2)
  /skills     → FilesystemBackend (pod disk, read-only)
  default     → StateBackend (in-memory scratch, from deepagents)

Adding a new backend: implement BackendProtocol in a new module here,
then register it in brain.py's CompositeBackend routes.
"""

from agent.backends.s3 import EAFBackend

__all__ = ["EAFBackend"]
