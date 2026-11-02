"""G2 (SK, 31 Oct 2026, after defect 36): the server refuses a vw tool older than its minimum by name, so a laptop that was not updated is told to update.
Raised to 0.65.0 with the design/126 build: its server reads the new tool's commands."""
from app.config import Settings
from app.main import plugin_refusal


def test_an_older_tool_is_told_to_update_and_0_70_0_passes():   # design/142 raised it to 0.70.0 (SK, 2 Nov 2026)
    minimum = Settings.model_fields['PLUGIN_MIN_VERSION'].default
    assert minimum == '0.70.0'
    said = plugin_refusal('/api/runs/x/visuals/images', '0.69.0', minimum)
    assert said and '0.69.0' in said and '0.70.0' in said and 'update it' in said
    assert plugin_refusal('/api/runs/x/visuals/images', '0.70.0', minimum) is None and plugin_refusal('/api/runs/x', '0.70.1', minimum) is None
