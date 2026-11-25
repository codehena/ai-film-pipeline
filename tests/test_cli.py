from pipeline.__main__ import main


def test_validate_command_succeeds(capsys):
    assert main(["validate"]) == 0
    assert "storyboard OK" in capsys.readouterr().out


def test_validate_reports_broken_storyboard(tmp_path, capsys):
    bad = tmp_path / "storyboard.json"
    bad.write_text('{"version": 1}', encoding="utf-8")
    assert main(["--storyboard", str(bad), "validate"]) == 1
    assert "problem" in capsys.readouterr().err


def test_unbuilt_stage_says_so(capsys, monkeypatch):
    from pipeline import __main__ as cli
    from pipeline.common import NotBuiltYet

    def unbuilt(storyboard, only=None):
        raise NotBuiltYet("demo stage")
    monkeypatch.setitem(cli.STAGES, "music", unbuilt)   # no real stage is called
    assert main(["music"]) == 2
    assert "not built yet" in capsys.readouterr().err
