# Compiler speculation tracing

When the Inmanta compiler's scheduler cannot determine that a list relation is complete,
it *speculates* by freezing the list — assuming no more items will be added. This is
necessary for `[0:]` relations where the compiler has no upper bound on the number of
items.

Excessive speculation can significantly impact compile performance. The speculation
tracing feature helps diagnose where and why the compiler speculates, enabling targeted
model or compiler optimizations.

## Generating a speculation log

Set the `INMANTA_SPECULATION_LOG` environment variable to a file path before running
a compile:

```bash
INMANTA_SPECULATION_LOG=/tmp/speculation.json inmanta compile
```

The compiler writes a JSON log containing every scheduler iteration and every
speculative freeze decision. The log is written at the end of compilation. There is
no measurable performance overhead — the instrumentation is skipped entirely when the
environment variable is not set.

## Analyzing the log

Use the analysis tool included in the repository:

```bash
python misc/analyze_speculation.py /tmp/speculation.json
```

This produces a summary with:

- **Progress source distribution** — how often the scheduler made progress via the
  normal waitqueue vs speculative freezing (`find_wait_cycle`)
- **Frozen attributes** — which entity types and relation attributes were speculatively
  frozen, and how many times each
- **Speculation phases** — groups of consecutive freezes on the same attribute, showing
  the order in which the compiler speculates
- **Queue evolution** — how the number of remaining waiters, candidates, outstanding
  providers, and progress potential change over the speculation phases
- **Candidate distribution** — which attributes appear most often as freeze candidates
  across all `find_wait_cycle` calls

## Understanding the output

### Progress sources

Each scheduler iteration makes progress through one of these mechanisms:

| Source                 | Meaning                                                          |
| ---------------------- | ---------------------------------------------------------------- |
| `waitqueue`            | Normal execution: a variable was frozen from the wait queue      |
| `find_wait_cycle`      | Speculation: the scheduler had to guess which variable to freeze |
| `zerowaiters_promoted` | A zero-waiter variable gained waiters and was promoted           |
| `final_freeze`         | End of compilation: remaining variables frozen unconditionally   |

A high ratio of `find_wait_cycle` to `waitqueue` indicates the model has patterns that
prevent the compiler from determining list completeness.

### Frozen attributes

This section shows which `entity_type.attribute` combinations are being speculatively
frozen. High counts on a single attribute indicate a systemic issue — usually a `[0:]`
relation that many instances share, combined with something that reads the list before
it is naturally complete.

### Speculation phases

Phases group consecutive freezes on the same attribute. A phase with count 95 on
`Rule.destination` means 95 different Rule instances each had their `destination`
relation speculatively frozen in sequence.

### Common causes of speculation

1. **Plugin calls that read list relations** — A plugin function receives its arguments
   as fully resolved Python values, forcing any list relation arguments to be frozen
   before the plugin can execute. If the list is still being populated, the compiler
   must speculate.

   *Fix:* Replace the plugin call with a pure DSL expression where possible. The DSL
   `is defined` check supports gradual execution — it returns `true` as soon as any
   element exists, without waiting for the list to be frozen.

2. **Reading a list in the same constructor that populates it** — If entity `A`'s
   constructor expression reads `a.some_list`, but `some_list` is populated by an
   implementation that runs after construction, the compiler is forced to speculate.

   *Fix:* Move the read to a separate implementation, or restructure so the list is
   populated before it is read.

3. **Co-dependent lists** — Two list relations that read each other (e.g., `purged`
   depends on both `source` and `destination`) create a cycle that requires speculation
   on both.

   *Fix:* Break the cycle by computing the dependent value from the upstream data
   (before it flows into the lists) rather than reading the lists themselves.

## Example: diagnosing a customer project

Running the tool on a project with 95 firewall rules:

```
Speculation log: /tmp/speculation.json
  Iterations: 1064
  Speculative freezes: 236

Frozen attributes (7 distinct):
     95  checkpoint::Rule.destination
     95  checkpoint::Rule.source
     12  tenant::Host.network_interfaces
     ...

Speculation phases:
    #   Start   Count  Attribute
    1     312       2  Environment.firewall_contexts_with_gateway
    2     635      12  Host.network_interfaces
    ...
    5+    766     190  Rule.destination / Rule.source (alternating)
  195    1010      11  AnonymousNamedObject.effective_members
```

This reveals that 190 of 236 freezes (80%) are on `Rule.source` and `Rule.destination`.
The root cause was a plugin call `empty_source_or_destination(rule.source, rule.destination)`
in the `purged` expression that forced both lists to freeze. Replacing it with the DSL
expression `not (rule.source is defined and rule.destination is defined)` eliminated
the speculation on those attributes.
