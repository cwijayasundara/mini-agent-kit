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
- [x] 6. Agent loop run(): steps, max_steps, error stop reasons
  verify: uv run pytest -q tests/test_agent.py
  done: ce55ac7
  after: 4, 5
- [x] 7. Run trace JSON round-trip
  verify: uv run pytest -q tests/test_trace.py
  done: c909795
  after: 6
- [x] 8. Toy tools: calculator parser, word_count, clock
  verify: uv run pytest -q tests/test_toys.py
  done: 67281e3
  after: 4
- [x] 9. CLI demo and run commands with bundled demo.json
  verify: uv run pytest -q tests/test_cli.py
  done: 606fcd9
  after: 7, 8
- [x] 10. README and all gates green
  verify: grep -q "register" README.md && python3 -B .factory/gates/tests.py && python3 -B .factory/gates/crap.py && python3 -B .factory/gates/dry.py
  done: 68d3780
  after: 9
- [x] 11. Demo prints the exact four lines
  verify: uv run mini-agent demo
  done: 68d3780
  after: 10
- [x] 12. Opt-in Fireworks provider, `demo --live` and `live` (intent/001)
  verify: uv run pytest -q tests/test_fireworks.py
  done: a1aecc0
  after: 11
- [x] 13. Eval suite and traced-run wrapper (intent/002)
  verify: uv run pytest -q tests/test_evals.py
  done: 5b8b3af
  after: 12
- [x] 14. Live evals, metrics and fix-mode guard (intent/002)
  verify: uv run pytest -q tests/test_evals.py tests/test_metrics.py
  done: da88328
  after: 13
- [x] 15. More evals, security scans in CI, drift tiers, rework metric (intent/002)
  verify: uv run pytest -q tests/test_drift.py
  done: 9e2c12b
  after: 14
- [x] 16. Eval-derived trace set and weekly drift job (intent/003)
  verify: uv run pytest -q tests/test_eval_traces.py
  done: 03415a0
  after: 15
- [x] 17. DORA-style metrics and plan-to-diff drift (intent/003)
  verify: uv run pytest -q tests/test_metrics.py
  done: 03415a0
  after: 15
- [x] 18. Evals for model-failure stops and bool-vs-string arguments
  verify: uv run pytest -q tests/test_evals.py
  done: 03415a0
  after: 15
- [x] 19. SDLC rehearsal on greenfield and brownfield repos (intent/004)
  verify: uv run pytest -q tests/test_sdlc_rehearsal.py
  done: 7ba4edf
  after: 18
- [x] 20. Live SDLC pass with a cheap builder and a stronger evaluator (intent/004)
  verify: uv run python -c "import ast,pathlib;ast.parse(pathlib.Path('tools/sdlc_live.py').read_text())"
  done: da03948
  after: 19
- [x] 21. Policy skills and policy tests (intent/005)
  verify: uv run pytest -q tests/test_policy.py
  done: 352a15d
  after: 20
- [ ] 22. Live brownfield SDLC pass (intent/004)
  verify: uv run pytest -q tests/test_policy.py
  after: 21
