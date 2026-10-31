"""G2 (SK, 31 Oct 2026, after defect 36): the server refuses a vw tool older than 0.64.1 by name, so a laptop that was not updated is told to update."""
from app.config import Settings
from app.main import plugin_refusal


def test_an_older_tool_is_told_to_update_and_0_64_1_passes():
    minimum = Settings.model_fields['PLUGIN_MIN_VERSION'].default
    assert minimum == '0.64.3'
    said = plugin_refusal('/api/runs/x/visuals/images', '0.64.2', minimum)
    assert said and '0.64.2' in said and '0.64.3' in said and 'update it' in said
    assert plugin_refusal('/api/runs/x/visuals/images', '0.64.3', minimum) is None and plugin_refusal('/api/runs/x', '0.65.0', minimum) is None
