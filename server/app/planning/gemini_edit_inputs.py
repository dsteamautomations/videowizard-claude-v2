

def passage_windows(context):
    """Partition the fixed section at existing passage starts, without moving audio."""
    starts = [min(word['timeline_start_s'] for word in context['mapped_words'] if word['passage_id'] == passage)
              for passage in context['passage_ids']]
    starts[0] = 0
    ends = starts[1:] + [context['duration_frames'] / context['fps']]
    return [{'passage_id': passage, 'timeline_start_s': start, 'timeline_end_s': end,
             'duration_s': round(end - start, 9)}
            for passage, start, end in zip(context['passage_ids'], starts, ends)]
