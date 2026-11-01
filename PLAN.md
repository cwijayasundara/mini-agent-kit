# PLAN

- [x] 1. Project scaffold: pyproject (uv, dev deps, console script), package imports, shared message/reply/error types
  verify: uv run python -c "import mini_agent_kit.types" && uv run pytest -q tests/test_types.py
  done: f8c5395
- [x] 2. Tool registry: register/@tool, name, description, docstring required
  verify: uv run pytest -q tests/test_registry_register.py
  done: 926dab9
  after: 1
- [x] 3. Schema derivation from type hints (str,int,float,bool,list,Literal), TypeError on others, schemas() sorted
  verify: uv run pytest -q tests/test_registry_schema.py
  done: 926dab9
  after: 2
- [x] 4. registry.call validation and ToolError messages, bool not int
  verify: uv run pytest -q tests/test_registry_call.py
  done: 926dab9
  after: 3
- [x] 5. ScriptedModel: load, validate script, next turn, expect, ScriptMismatch, ScriptExhausted
  verify: uv run pytest -q tests/test_scripted.py
  done: 173a90b
  after: 1
- [ ] 6. Agent loop run(): steps, max_steps, error stop reasons
  verify: uv run pytest -q tests/test_agent.py
  after: 4, 5
- [ ] 7. Run trace JSON round-trip
  verify: uv run pytest -q tests/test_trace.py
  after: 6
- [ ] 8. Toy tools: calculator parser, word_count, clock
  verify: uv run pytest -q tests/test_toys.py
  after: 4
- [ ] 9. CLI demo and run commands with bundled demo.json
  verify: uv run pytest -q tests/test_cli.py
  after: 7, 8
- [ ] 10. README and all gates green
  verify: grep -q "register" README.md && python3 -B .factory/gates/tests.py && python3 -B .factory/gates/crap.py && python3 -B .factory/gates/dry.py
  after: 9
- [ ] 11. Demo prints the exact four lines
  verify: uv run mini-agent demo
  after: 10
