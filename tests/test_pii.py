from app.pii import scrub_text


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_scrub_cccd() -> None:
    cccd = "079203001234"
    out = scrub_text(f"Số CCCD của tôi là {cccd}")
    assert cccd not in out
    assert "REDACTED_CCCD" in out


def test_scrub_credit_card() -> None:
    cards = (
        "4532-1111-2222-3333",
        "4532 1111 2222 3333",
        "4532111122223333",
    )
    for card in cards:
        out = scrub_text(f"Thẻ thanh toán: {card}")
        assert card not in out
        assert "REDACTED_CREDIT_CARD" in out

