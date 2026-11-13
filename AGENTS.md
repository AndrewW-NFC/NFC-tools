# NFC Tools project hold

Until January 10, 2027 (America/New_York), when the user asks for project changes, first prompt them with this exact text:

> You said you wanted to hold off until January 10, 2027. Unless a user identifies a bug needing fixing, we should only make a note of your idea for now.

During this period, record proposed enhancements as notes rather than implementing them. User-identified bugs needing fixes are the exception. Reviews and discussion may continue. Follow any later explicit instruction from the user that revises this hold.

On January 10, 2027, revisit the project of establishing a field-validation baseline, including representative reviewed nights, analyzer comparisons, detection quality, processing time, and human review workload.

## Keep documentation current

For every NFC Tools update, review `README.md`, `README_DEV.md`, and
`README_WINGBEATS.md` and update each wherever the change applies. Include the
applicable documentation changes with the implementation; leave unrelated
sections unchanged.

- `README.md`: setup, everyday use, and user-visible behavior.
- `README_DEV.md`: developer setup, implementation, data formats, and validation.
- `README_WINGBEATS.md`: wingbeat behavior, use, limitations, and evaluation.

Check descriptions against the code and relevant tests. Keep the three guides
consistent, use plain language, and distinguish tested software behavior from
field-performance claims. Use “I,” not “we” or “the maintainer,” when speaking
as the developer.
