from app.services.article import calculate_content_hash


def test_calculate_content_hash() -> None:
    result = calculate_content_hash("hello")

    assert result == ("2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824")
    assert len(result) == 64


def test_different_content_produces_different_hashes() -> None:
    first_hash = calculate_content_hash("第一篇文章")
    second_hash = calculate_content_hash("第二篇文章")

    assert first_hash != second_hash
