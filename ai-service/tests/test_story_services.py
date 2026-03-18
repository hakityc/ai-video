from app.story.service import generate_story_card
from app.storyboard.service import generate_storyboard


def test_story_card_has_required_fields():
    payload = {
        "project": {"style": "cinematic"},
        "episode": {"title": "雨夜便利店", "logline": "主角发现录音笔"},
        "characters": [],
        "locations": [],
    }
    result = generate_story_card(payload)
    assert result.theme
    assert result.conflict
    assert result.twist
    assert result.ending_hook
    assert result.summary


def test_storyboard_returns_shots_in_duration_range():
    payload = {
        "project": {"style": "cinematic"},
        "episode": {"title": "雨夜便利店", "logline": "主角发现录音笔"},
        "story_card": {"summary": "主角在便利店发现录音笔"},
        "characters": [],
        "locations": [],
    }
    result = generate_storyboard(payload)
    assert result.scenes
    assert result.shots
    assert all(3 <= shot.duration <= 8 for shot in result.shots)
