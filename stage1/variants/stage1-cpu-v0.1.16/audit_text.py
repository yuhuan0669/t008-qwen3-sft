"""Lexical overlap only; it cannot prove semantic independence."""
import re

def shared_fragments(left, right, width=12):
    if width < 1:
        raise ValueError('width must be positive')
    def fragments(turns):
        result = set()
        for turn in turns:
            text = re.sub(r'\s+', '', turn).casefold()
            result.update(text[i:i + width] for i in range(len(text) - width + 1))
        return result
    return fragments(left) & fragments(right)
