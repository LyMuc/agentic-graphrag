"""Back-compat shim — tách sang ``server.agents.direct`` (Phase 3).

- ``respond`` (answer_given) -> ``server.agents.direct.respond``
- ``clarify`` (clarify_question) -> ``server.agents.direct.clarify``
"""
from server.agents.direct.respond import (  # noqa: F401
    RespondAgent,
    answer_given,
    answer_given_description,
)
from server.agents.direct.clarify import (  # noqa: F401
    ClarifyAgent,
    clarify_question,
    clarify_description,
)
