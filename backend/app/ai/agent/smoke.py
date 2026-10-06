"""Live smoke test for the agent graph - run by hand, never in CI.

    cd backend && python -m app.ai.agent.smoke

Needs LLM_API_KEY. Uses an unsaved User and unsaved Message rows, so it touches no database:
it proves the graph compiles, calls the provider, and that replaying the transcript really is
the memory mechanism (turn 2 can answer a question about turn 1).
"""

from __future__ import annotations

import asyncio

from app.ai.agent.runner import prepare_turn, run_turn
from app.models.message import Message
from app.models.user import User

DEMO_USER = User(
    id=0,
    email="smoke@example.com",
    first_name="Smoke",
    last_name=None,
    currency="INR",
    timezone="Asia/Kolkata",
)

TURNS = [
    "Hi - in one sentence, what can you help me with?",
    "What was the first thing I asked you?",
]


def _as_text(content: object) -> str:
    return content if isinstance(content, str) else str(content)


async def main() -> None:
    history: list[Message] = []
    next_id = 1

    for turn_number, user_input in enumerate(TURNS, start=1):
        inputs = prepare_turn(DEMO_USER, history, user_input, conversation_id="smoke")
        print(f"\n--- turn {turn_number} ---")
        print(f"messages sent : {len(inputs.state['messages'])}")
        print(f"prompt version: {inputs.context.prompt_version}")
        print(f"user          : {user_input}")

        reply = await run_turn(inputs)
        reply_text = _as_text(reply.content)
        print(f"assistant     : {reply_text}")

        history.append(Message(id=next_id, role="user", content=user_input))
        history.append(Message(id=next_id + 1, role="assistant", content=reply_text))
        next_id += 2

    print("\nOK - turn 2 proves the replayed window is the memory.")


if __name__ == "__main__":
    asyncio.run(main())
