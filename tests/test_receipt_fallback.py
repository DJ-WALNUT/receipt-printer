import receipt


def test_fallbacks_cover_windows_and_linux_and_missing_paths_are_skipped():
    paths = [str(p).replace("\\", "/").lower() for p, _ in receipt.FALLBACKS]
    assert any("unifont" in p for p in paths)       # 라즈베리파이 (fonts-unifont)
    assert any("msgothic" in p for p in paths)      # Windows
    assert receipt.render(["漢字 테스트 かな"]).width == receipt.PAPER_W   # 어느 OS에서도 오류 없이 그려진다
