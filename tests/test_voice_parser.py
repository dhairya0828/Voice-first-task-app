from datetime import datetime, timezone

from app.services.voice_parser import interpret_voice_command


def test_create_command_extracts_title_and_due_date() -> None:
    now = datetime(2026, 3, 9, tzinfo=timezone.utc)
    interpretation = interpret_voice_command("Remind me to submit quarterly report by next friday", now=now)

    assert interpretation.action == "create"
    assert interpretation.extracted_title is not None
    assert "submit quarterly report" in interpretation.extracted_title.lower()
    assert interpretation.extracted_due_date is not None


def test_complete_command_extracts_query() -> None:
    interpretation = interpret_voice_command("Complete task prepare team deck")

    assert interpretation.action == "complete"
    assert interpretation.task_query is not None
    assert "prepare team deck" in interpretation.task_query.lower()


def test_delay_command_extracts_days() -> None:
    interpretation = interpret_voice_command("Delay task sprint review by 2 days")

    assert interpretation.action == "delay"
    assert interpretation.delay_days == 2
    assert interpretation.task_query is not None
