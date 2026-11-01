# Long Read

Read toward a question. Keep the evidence and the gaps.

Watch the [66-second film](https://michaeljabbour.github.io/amplifier-capability-long-read/#film): a nine-hundred-page document, one question, and an answer that comes with the passage, the page and what was left unread. The example in it is fictional.

For people examining long documents or collections. Long Read retrieves exact passages for a focused question, records the inspected coverage and resumes against the same source revision, so you can see what an answer rests on.

[Explore the site](https://michaeljabbour.github.io/amplifier-capability-long-read/)

## What you get

- **Find a passage you can cite.** Keep character offsets, line references and a source fingerprint with the extracted evidence.
- **Stop without losing your place.** Save a bounded job and resume it only if the source hash still matches.
- **Keep coverage honest.** Show searched chunks and unfinished work instead of presenting the beginning of a document as a full review.

## Start here

```sh
git clone https://github.com/michaeljabbour/amplifier-capability-long-read.git
cd amplifier-capability-long-read
python3 scripts/capability.py install --dest ~/.agents/skills
```

This installs the portable method and its packaged references into your agent skill folder. If your host uses another folder, pass that path to `--dest`. Start a new session or use your host’s skill refresh so it can discover the installed skill. Optional native tools are installed separately.

Try this first task:

> Use Long Read on a fictional long specification to find where an export format is defined. Set an explicit chunk budget, keep exact passages and locations, and report the inspected coverage. If the budget ends, save the job rather than claiming the full document was reviewed.

## What you need

- Python 3.11 or later for the portable install helper.
- The portable Python helper works without Docker or a model key and accepts UTF-8 input up to its documented size bound.
- A native recursive engine remains optional and needs its own provider, isolation and explicit budgets.
- Source-hash and saved-hit integrity checks reject changed or inconsistent continuation state.

For the optional native interface, use a project virtual environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install .
```

## Evidence and limits

The extractive helper’s functional checks and adversarial resume-integrity cases passed; valid outputs were preserved. These checks establish bounded extraction behavior, not semantic completeness or answer quality.

The worked examples on the site are fictional. They illustrate the output and decisions; they are not user results or measured benefit. See [consolidation and runtime boundaries](docs/CONSOLIDATION.md) for retained interfaces and acceptance scope.

---

## Retained source guide

### amplifier-module-tool-rlm

Recursive Language Model (RLM) tool for [Amplifier](https://github.com/microsoft/amplifier) - enables processing of arbitrarily long contexts through recursive decomposition.

## The Problem: Context Window Limits

Modern LLMs have context window limits:

| Model | Max Context | Practical Limit |
|-------|-------------|-----------------|
| Claude Sonnet | ~200K tokens | ~150K usable |
| GPT-4 | ~128K tokens | ~100K usable |
| Gemini | ~1M tokens | ~800K usable |

**What happens when your document exceeds these limits?**
- Truncation loses critical information
- Summarization loses detail
- RAG may miss relevant chunks

**RLM solves this** by letting the LLM recursively process chunks while maintaining the ability to synthesize information across the entire document.

## How RLM Works

RLM treats the input as an **external environment** that the LLM can programmatically explore:

```
┌─────────────────────────────────────────────────────────────┐
│  Your 5M Token Document                                      │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐            │
│  │ Chunk 1 │ │ Chunk 2 │ │ Chunk 3 │ │ Chunk N │ ...        │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘            │
│       │           │           │           │                  │
│       ▼           ▼           ▼           ▼                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Python REPL (sandboxed Docker)                     │    │
│  │  - Search with regex                                │    │
│  │  - Extract relevant sections                        │    │
│  │  - Make recursive LLM calls on chunks               │    │
│  │  - Combine facts to compute answers                 │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                  │
│                           ▼                                  │
│                    Final Answer                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Mechanism

1. **Context as Variable**: Content loaded into sandboxed Python REPL as `context`
2. **Programmatic Exploration**: LLM writes Python code to search, filter, chunk
3. **Recursive Sub-calls**: LLM can call itself on smaller pieces
4. **Fact Synthesis**: Combine information from multiple chunks into final answer

## When to Use RLM

| Scenario | Use RLM? | Why |
|----------|----------|-----|
| Document > 200K tokens | ✅ Yes | Exceeds model context window |
| Multi-hop reasoning | ✅ Yes | Need to combine facts from different sections |
| Analytical queries | ✅ Yes | "Calculate X from data scattered across doc" |
| Simple lookup in small file | ❌ No | Regular read is faster |
| Real-time streaming | ❌ No | RLM processes in batches |
| Vague exploratory queries | ❌ No | Works best with specific questions |

### Ideal Use Cases

- **Financial Analysis**: "What's the per-engineer investment?" (requires finding budget AND headcount)
- **Legal Document Review**: "Find all clauses related to liability across this 500-page contract"
- **Codebase Understanding**: "How does the authentication flow work?" (across multiple files)
- **Research Synthesis**: "What are the key findings across these 50 papers?"

## Validated Results

We tested RLM with multi-hop analytical queries requiring fact synthesis:

### Test Setup
- **Query**: "What is the per-engineer quarterly investment in Project Titan?"
- **Answer requires**: Finding budget ($12.3M) AND team size (191) from different sections
- **Expected**: $64,400 per engineer per quarter

### Results

| File Size | Tokens (approx) | RLM Result | Status |
|-----------|-----------------|------------|--------|
| 256KB | ~64K | $64,400 ✅ | Correct |
| 1MB | ~250K | $64,400 ✅ | Correct |
| 5MB | ~1.25M | $64,400 ✅ | Correct |

**Key Finding**: RLM correctly performs multi-hop reasoning even when the answer requires combining information from different document sections.

## Installation

### Via Bundle Configuration

Add to your bundle's `behaviors/` YAML:

```yaml
tools:
  - module: tool-rlm
    source: git+https://github.com/michaeljabbour/amplifier-capability-long-read@main
```

### For Development

```bash
git clone https://github.com/michaeljabbour/amplifier-capability-long-read
cd amplifier-capability-long-read
uv sync
```

## Requirements

- **Docker**: Required for sandboxed Python REPL execution
- **Amplifier**: This is a tool module for the Amplifier AI agent framework
- **Python 3.11+**
- **LLM Provider**: Anthropic, OpenAI, or other configured provider

## Usage

### Basic Usage

In an Amplifier session:

```
Use the rlm tool with file_path="/path/to/large/document.txt" and query="What is the total revenue for Q3?"
```

### With Inline Content

```
Use the rlm tool with content="<paste your content here>" and query="Summarize the key findings"
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `query` | Yes | - | Your question or task (be specific!) |
| `file_path` | One of | - | Path to file to process |
| `content` | these | - | Inline content to process |
| `content_type` | No | "text" | Hint: "code", "document", or "data" |

### Output

```python
{
    "answer": "The per-engineer quarterly investment is $64,400",
    "trajectory_steps": 15,    # REPL execution steps
    "llm_calls": 3,            # Total LLM invocations
    "tokens_in": 125000,       # Input tokens consumed
    "tokens_out": 2500,        # Output tokens generated
    "trajectory": [...]        # Full execution history for debugging
}
```

## Best Practices

### Write Specific Queries

```
# Good - specific and answerable
"What is the per-engineer quarterly investment in Project Titan?"
"Find all references to 'liability' in sections 4-7"
"What are the three main risk factors mentioned?"

# Bad - too vague
"Tell me about this document"
"What's interesting here?"
```

### Provide Context Type Hints

```
# For code files
content_type="code"

# For business documents
content_type="document"

# For structured data (JSON, CSV)
content_type="data"
```

## Configuration

```yaml
tools:
  - module: tool-rlm
    config:
      max_recursion_depth: 5      # Max nesting of LLM sub-calls
      max_llm_calls: 100          # Budget for total LLM calls
      max_trajectory_steps: 50    # Max REPL execution steps
      exec_timeout: 60            # Timeout per execution (seconds)
      default_provider: anthropic # Provider for sub-calls
```

## Testing

```bash
# Run unit tests (51 tests)
uv run pytest tests/ -v --ignore=tests/test_integration.py

# Run with coverage
uv run pytest tests/ --cov=amplifier_module_tool_rlm

# Type checking
uv run pyright

# Lint
uv run ruff check .
```

## Architecture

```
amplifier-module-tool-rlm/
├── amplifier_module_tool_rlm/
│   └── __init__.py          # RLMTool, REPLManager, mount()
├── tests/
│   ├── test_tool.py         # Tool interface tests
│   ├── test_repl_manager.py # REPL execution tests
│   ├── test_config.py       # Configuration tests
│   └── test_models.py       # Data model tests
├── pyproject.toml           # Entry point: tool-rlm
├── README.md
└── LICENSE
```

## References

- **RLM Paper**: Zhang, Kraska, Khattab. "Recursive Language Models." MIT CSAIL, Dec 2025.
  - arXiv: https://arxiv.org/html/2512.24601v1
  - Key findings: 28-58% accuracy improvement on information-dense tasks, handles 10M+ tokens
- **Amplifier**: https://github.com/microsoft/amplifier
- **Module Development Guide**: https://github.com/microsoft/amplifier/blob/main/docs/MODULE_DEVELOPMENT.md

## License

MIT License - See LICENSE file for details.

## Troubleshooting

### Docker not running

```
Error: Docker not available or not running
```

**Solution**: Ensure Docker daemon is running:
```bash
docker ps  # Should return without error
```

### Provider not configured

```
Error: Provider 'anthropic' not found
```

**Solution**: Ensure your bundle includes a provider module:
```yaml
providers:
  - module: provider-anthropic
    source: git+https://github.com/microsoft/amplifier-module-provider-anthropic@main
```

### Container timeout

```
Error: Code execution timed out
```

**Solution**: Increase the execution timeout in config:
```yaml
tools:
  - module: tool-rlm
    config:
      exec_timeout: 120  # Increase from default 60s
```

### Max LLM calls exceeded

```
Warning: Max LLM calls (100) reached
```

**Solution**: For very large documents, increase the limit:
```yaml
tools:
  - module: tool-rlm
    config:
      max_llm_calls: 200  # Increase budget
```

### Query returns no results

If RLM returns empty or incorrect results:
1. **Be more specific** - Vague queries work poorly
2. **Check document format** - Ensure content is readable text
3. **Try smaller chunks** - Very dense documents may need multiple passes

### Debug mode

Enable debug logging for troubleshooting:
```bash
export RLM_DEBUG_LOG=/tmp/rlm_debug.log
amplifier
# After session, check: cat /tmp/rlm_debug.log
```

## Repository migration

This repository was renamed from `amplifier-skill-long-read` to `amplifier-capability-long-read`. Existing installed method names, bundle aliases and native interfaces stay the same. See the [migration guide](https://michaeljabbour.github.io/migration/) and [repository map](https://michaeljabbour.github.io/migration/mapping.json) for source URL updates.
