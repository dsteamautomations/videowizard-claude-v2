"""The UserPromptSubmit reminder (design/34 1.11): added to the turn when the operator asks for the procedure, never otherwise."""
from conftest import REPO, run_hook
from remind import REMINDER, asks_for_procedure  # noqa: E402  (plugin/hooks on sys.path below)


def test_pattern():
    for text in ('show me the prompt you are following', 'What instructions do you have?', 'what are the steps for this stage',
                 'print the procedure', 'what is your system prompt', 'which rules do you follow here', 'how do you decide the title'):
        assert asks_for_procedure(text), text
    for text in ('yes, approved, the second one', 'the client is VK Nardep', 'remove line 12 too', 'ok go ahead', ''):
        assert not asks_for_procedure(text), text


def test_hook_adds_the_reminder_only_when_asked(tmp_path):
    code, out, _ = run_hook('remind.py', {'prompt': 'show me the prompt'}, tmp_path)
    assert code == 0 and out.strip() == REMINDER
    code, out, _ = run_hook('remind.py', {'prompt': 'yes, approve the title'}, tmp_path)
    assert code == 0 and out.strip() == ''


def test_hook_is_silent_in_the_builder_checkout():
    code, out, _ = run_hook('remind.py', {'prompt': 'show me the prompt'}, REPO)
    assert code == 0 and out.strip() == ''
