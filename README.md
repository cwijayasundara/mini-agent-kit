# mini-agent-kit

A tiny offline toolkit for tool-using agents, tested with a scripted fake model.
Built unattended from [SPEC.md](SPEC.md) by the lights-on factory's build mode.

## Register a tool and run an agent

```python
from mini_agent_kit.agent import run
from mini_agent_kit.registry import Registry
from mini_agent_kit.scripted import ScriptedModel

registry = Registry()


@registry.tool
def shout(text: str) -> str:
    """Upper-case some text."""
    return text.upper()


model = ScriptedModel(
    {
        "turns": [
            {
                "tool_calls": [
                    {"id": "c1", "name": "shout", "arguments": {"text": "hi"}}
                ]
            },
            {"expect": {"c1": "HI"}, "final": "done"},
        ]
    }
)
print(run("say hi loudly", model, registry).answer)  # done
```

A tool's name is the function name, its description is the docstring's first
paragraph, and its input schema comes from the type hints. You can also call
`registry.register(fn)` directly instead of using the decorator.

## Run the demo

```
uv run mini-agent demo
uv run mini-agent run --script my_script.json --trace trace.json "my question"
```

`demo` and `run` are offline: no network or API keys are needed.

## Live model (Fireworks)

`FireworksModel` plans with a real LLM through the Fireworks chat-completions
API (default model `accounts/fireworks/models/glm-5p3-flash`). It uses only the
standard library.

```
export FIREWORKS_API_KEY=...
uv run mini-agent demo --live
uv run mini-agent live --trace trace.json "what is 12 * 12?"
```

Without the key these commands print an error and exit with code 2. Replies are
free text, so wording varies run to run. Any other provider only has to
implement `Model.complete(messages, tools)`.
