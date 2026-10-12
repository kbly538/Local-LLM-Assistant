import argparse
import logging
import os
import sys
from typing import cast

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
)
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageFunctionToolCall,
    ChatCompletionMessageParam,
    ChatCompletionToolMessageParam,
)

from aiagent.config import (
    CONTEXT_LIMIT,
    MAX_AGENT_ITERATIONS,
    MODEL,
    TEMPERATURE,
    TIMEOUT,
)
from aiagent.prompts import system_prompt
from aiagent.tools.dispatcher import (
    available_functions,
    call_function,
)

logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="QB AI Agent")

    parser.add_argument(
        "user_prompt",
        nargs="?",
        type=str,
        help="Initial user prompt",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    load_dotenv()

    api_key = os.environ.get(
        "OPENROUTER_API_KEY",
        "ollama",
    )

    client = OpenAI(
        base_url="http://localhost:11434/v1",
        api_key=api_key,
        timeout=TIMEOUT,
        max_retries=1,
    )

    messages: list[ChatCompletionMessageParam] = [
        {
            "role": "system",
            "content": system_prompt,
        },
    ]

    # Komut satırından ilk prompt verilmişse onu kullan.
    pending_prompt = args.user_prompt

    print("QB AI Agent")
    print("Exit için: exit, quit veya Ctrl+C")

    try:
        while True:
            if pending_prompt is not None:
                user_prompt = pending_prompt
                pending_prompt = None
            else:
                user_prompt = input("\nYou: ").strip()

            if not user_prompt:
                continue

            if user_prompt.lower() in {"exit", "quit"}:
                print("Goodbye.")
                return 0

            messages.append(
                {
                    "role": "user",
                    "content": user_prompt,
                }
            )

            response_text = run_agent_turn(
                client=client,
                messages=messages,
                verbose=args.verbose,
            )

            print(f"\nAgent: {response_text}")

    except KeyboardInterrupt:
        print("\nGoodbye.")
        return 0

    except APITimeoutError as error:
        print(
            "Error: Model request timed out before a response was completed.",
            file=sys.stderr,
        )

        if args.verbose:
            print(
                f"Details: {error}",
                file=sys.stderr,
            )

        return 1

    except APIConnectionError as error:
        print(
            "Error: Could not connect to the Ollama server.",
            file=sys.stderr,
        )

        if args.verbose:
            print(
                f"Cause: {error.__cause__}",
                file=sys.stderr,
            )

        return 1

    except AuthenticationError:
        print(
            "Error: Authentication failed.",
            file=sys.stderr,
        )
        return 1

    except APIStatusError as error:
        print(
            f"Error: Server responded with HTTP {error.status_code}.",
            file=sys.stderr,
        )
        return 1

    except Exception as error:
        logger.exception("Unexpected error")

        print(
            f"Error: Unexpected error: {type(error).__name__}: {error}",
            file=sys.stderr,
        )
        return 1


def run_agent_turn(
    client: OpenAI,
    messages: list[ChatCompletionMessageParam],
    verbose: bool,
) -> str:
    max_iterations = MAX_AGENT_ITERATIONS

    for iteration in range(MAX_AGENT_ITERATIONS):
        if verbose:
            print(f"\n--- Agent iteration {iteration + 1}/{MAX_AGENT_ITERATIONS} ---")

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=available_functions,
            temperature=TEMPERATURE,
        )

        if verbose and response.usage is not None:
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens

            context_limit = CONTEXT_LIMIT
            usage_percent = prompt_tokens / context_limit * 100

            print(f"Prompt tokens:     {prompt_tokens}")
            print(f"Completion tokens: {completion_tokens}")
            print(f"Total tokens:      {total_tokens}")
            print(
                f"Context usage:     "
                f"{prompt_tokens}/{context_limit} "
                f"({usage_percent:.1f}%)"
            )

        message = response.choices[0].message

        messages.append(
            cast(
                ChatCompletionAssistantMessageParam,
                message.model_dump(exclude_none=True),
            )
        )

        if not message.tool_calls:
            if message.content:
                return message.content

            return "Error: Model returned no content and no tool calls."

        for tool_call in message.tool_calls:
            if isinstance(
                tool_call,
                ChatCompletionMessageFunctionToolCall,
            ):
                result_message = call_function(
                    tool_call,
                    verbose=verbose,
                )
            else:
                result_message: ChatCompletionToolMessageParam = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": ("Error: Unsupported custom tool call."),
                }

            messages.append(result_message)

            if verbose:
                print(f"-> {result_message['content']}")

    return f"Error: Agent reached the maximum iteration limit of {max_iterations}."


if __name__ == "__main__":
    raise SystemExit(main())
