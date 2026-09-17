from __future__ import annotations

from pipeline.render.remotion import _remotion_cli


def test_remotion_cli_prefers_local_install(tmp_path):
    executable = tmp_path / "node_modules" / ".bin" / "remotion.cmd"
    executable.parent.mkdir(parents=True)
    executable.write_text("", encoding="utf-8")

    assert _remotion_cli(tmp_path) == [str(executable)]
