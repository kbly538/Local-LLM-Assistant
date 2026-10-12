import os

from bs4 import BeautifulSoup
from openai.types.chat import ChatCompletionToolUnionParam

from aiagent.tools.result import Result

SCHEMA_VALUDATE_HTML: ChatCompletionToolUnionParam = {
    "type": "function",
    "function": {
        "name": "validate_html",
        "description": (
            "Validates a static HTML file and reports structural or "
            "obviously invalid HTML/CSS content."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": ("Relative path of the HTML file to validate."),
                }
            },
            "required": ["file_path"],
            "additionalProperties": False,
        },
    },
}


def validate_html(
    working_directory: str,
    file_path: str,
) -> Result[str]:
    abs_working_directory = os.path.realpath(working_directory)
    target_file = os.path.realpath(os.path.join(abs_working_directory, file_path))

    if (
        os.path.commonpath([abs_working_directory, target_file])
        != abs_working_directory
    ):
        return Result.fail(
            f'Error: Cannot validate "{file_path}" because it is '
            "outside the permitted working directory."
        )

    if not os.path.isfile(target_file):
        return Result.fail(f'Error: "{file_path}" is not a file.')

    if not file_path.lower().endswith((".html", ".htm")):
        return Result.fail(f'Error: "{file_path}" is not an HTML file.')

    try:
        with open(target_file, encoding="utf-8") as file:
            content = file.read()

        errors: list[str] = []

        if "<!doctype html" not in content.lower():
            errors.append("Missing <!DOCTYPE html>.")

        if "<html" not in content.lower():
            errors.append("Missing <html> element.")

        if "<head" not in content.lower():
            errors.append("Missing <head> element.")

        if "<body" not in content.lower():
            errors.append("Missing <body> element.")

        suspicious_tokens = [
            "**",
            "height:flex",
            "width:flex",
            "@supports(hover):&",
            "@media(hover:not(motion))&",
            "background-image:**",
            "var(--i)+",
        ]

        for token in suspicious_tokens:
            if token in content:
                errors.append(f"Suspicious or invalid token found: {token}")

        soup = BeautifulSoup(content, "html5lib")

        if soup.html is None:
            errors.append("HTML parser could not create an html element.")

        if soup.head is None:
            errors.append("HTML parser could not create a head element.")

        if soup.body is None:
            errors.append("HTML parser could not create a body element.")

        if errors:
            return Result.fail("HTML validation failed:\n- " + "\n- ".join(errors))

        return Result.ok(
            f'HTML validation passed for "{file_path}" ({len(content)} characters).'
        )

    except UnicodeDecodeError:
        return Result.fail(f'Error: "{file_path}" is not valid UTF-8.')

    except OSError as error:
        return Result.fail(f"Error: Could not validate file: {error}")
