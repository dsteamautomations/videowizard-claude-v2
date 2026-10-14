"""User choices for a new run. No editorial inference or media dispatch."""
from copy import deepcopy
import json


FIRST_QUESTION = ("What kind of video are we making, and should recorded camera/microphone "
                  "audio be heard in the final output, or used only for understanding?")

CHOICES = {
    'source_audio_in_output': {'none', 'speech', 'ambient', 'both', 'unresolved'},
    'talking_heads': {'present', 'absent', 'to_be_assessed'},
    'visible_speaking': {'allow', 'avoid', 'selective', 'unresolved'},
    'story_carrier': {'supplied_narration', 'source_speech', 'mixed', 'unresolved'},
    'supplied_narration_policy': {'preserve', 'not_used', 'user_defined', 'unresolved'},
    'source_speech_under_b_roll': {'allow', 'avoid', 'unresolved'},
    'speaker_on_screen': {'allow', 'avoid', 'selected_moments', 'unresolved'},
}


def unresolved_situation():
    """Template only; each new run records its own conversation."""
    return dict(enabled=True, confirmed=False, situation_description='',
                **{key: 'to_be_assessed' if key == 'talking_heads' else 'unresolved'
                   for key in CHOICES}, visible_speaking_exceptions=[],
                supplied_narration_instructions='', speaker_selected_moments=[])


def validate_situation(value, require_resolved=False):
    if not isinstance(value, dict):
        raise ValueError('workflow_situation must be an object')
    if type(value.get('enabled')) is not bool:
        raise ValueError('workflow_situation.enabled must be a boolean')
    if not value['enabled']:
        return deepcopy(value)
    if type(value.get('confirmed')) is not bool:
        raise ValueError('workflow_situation.confirmed must be a boolean')
    for key, allowed in CHOICES.items():
        if not isinstance(value.get(key), str) or value[key] not in allowed:
            raise ValueError(f'workflow_situation.{key} must be one of {sorted(allowed)}')
    for key in ('situation_description', 'supplied_narration_instructions'):
        if not isinstance(value.get(key), str):
            raise ValueError(f'workflow_situation.{key} must be text')
    for key in ('visible_speaking_exceptions', 'speaker_selected_moments'):
        if not isinstance(value.get(key), list) or any(
                not isinstance(item, str) or not item.strip() for item in value[key]):
            raise ValueError(f'workflow_situation.{key} must be a list of nonempty descriptions')
    if value['visible_speaking'] == 'selective' and not value['visible_speaking_exceptions']:
        raise ValueError('Selective visible speaking needs concrete exceptions')
    if value['speaker_on_screen'] == 'selected_moments' and not value['speaker_selected_moments']:
        raise ValueError('Selected speaker moments need concrete descriptions')
    if value['supplied_narration_policy'] == 'user_defined' and not value['supplied_narration_instructions'].strip():
        raise ValueError('User-defined narration needs instructions')
    audio = value['source_audio_in_output']
    if audio in {'none', 'ambient'}:
        if value['story_carrier'] in {'source_speech', 'mixed'}:
            raise ValueError('Source speech cannot carry the story when output speech is disallowed')
        if value['source_speech_under_b_roll'] == 'allow':
            raise ValueError('Source speech under B-roll needs output speech permission')
    if value['visible_speaking'] == 'allow' and value['speaker_on_screen'] == 'avoid':
        raise ValueError('Allowing visible speaking conflicts with avoiding the speaker on screen')
    if value['story_carrier'] in {'supplied_narration', 'mixed'} and value['supplied_narration_policy'] == 'not_used':
        raise ValueError('The story carrier requires supplied narration')
    if require_resolved:
        if not value['confirmed'] or not value['situation_description'].strip():
            raise ValueError('Ask the first workflow question and record the user situation before dispatch')
        unresolved = [key for key in CHOICES if value[key] == 'unresolved']
        # This choice has no effect when recorded speech cannot enter the output.
        if audio in {'none', 'ambient'}:
            unresolved = [key for key in unresolved if key != 'source_speech_under_b_roll']
        if unresolved:
            raise ValueError('Clarify affected user choices before dispatch: ' + ', '.join(unresolved))
    return deepcopy(value)


def effective_situation(config, profile=None, require_resolved=False):
    value = (profile['workflow_situation'] if profile is not None and 'workflow_situation' in profile
             else config.get('workflow_situation'))
    if value is None:
        return None
    result = validate_situation(value, require_resolved=require_resolved)
    return result if result['enabled'] else None


def situation_prompt(value):
    situation = validate_situation(value, require_resolved=True)
    if not situation['enabled']:
        return ''
    return ('USER-CONFIRMED WORKFLOW SITUATION\n'
            'Original camera/microphone audio may be examined to understand the source even when '
            'it is forbidden in the final output. Output audio and visible speaking are separate choices. '
            'Apply the choices below instead of historical mute-camera or avoid-talking defaults. '
            'An allowed speaker may explain a process on screen. When permitted, source speech may '
            'continue under corresponding process B-roll. The planner chooses supported passages, coverage '
            'and placements; permission alone is not an instruction to use every speaker or utterance. '
            'Avoid visible speaking does not ban people working silently. to_be_assessed means inspect '
            'for talking heads, not assume they are absent. Respect all source exclusions. '
            'Give concise evidence-based editorial reasons, script connections, intended viewing '
            'and limits, not private reasoning.\n' + json.dumps(situation, ensure_ascii=False, sort_keys=True))
