---
name: instruments-profiling
description: >
  Analyze macOS Instruments.app trace files (.trace) using Xcode CLI tools (xctrace, sample,
  spindump) to diagnose performance problems — CPU hotspots, main-thread hangs, lock contention,
  and more. Use this skill whenever the user mentions Instruments traces, .trace files, CPU
  profiling, hang analysis, performance profiling on macOS, or wants help diagnosing why their
  app is slow, hanging, or using too much CPU. Also use when the user provides a path to a
  .trace file or asks about xctrace.
---

# Instruments Trace Analysis

This skill turns Instruments `.trace` files into actionable performance insights using CLI
tools, without requiring the user to manually navigate the Instruments GUI.

## Available CLI Tools

| Tool | Purpose | How to find it |
|------|---------|---------------|
| `xctrace` | Export `.trace` data to parseable XML | `xcrun --find xctrace` |
| `sample` | Lightweight sampling profiler — attach to a running process | `/usr/bin/sample` |
| `spindump` | Capture hang/spin reports from a running process | `/usr/sbin/spindump` |

`xctrace export` is the primary tool. The others are useful when the user doesn't have a
`.trace` file yet and wants to capture data from a running process.

## Workflow: Analyzing a .trace File

### Step 1: Discover what's in the trace

```bash
xctrace export --input "path/to/file.trace" --toc
```

This returns XML describing every run and table in the trace. Look for:
- `<run number="N">` — each recording session is a separate run
- `<table schema="...">` — the data tables available

**Key table schemas:**
- `cpu-profile` — CPU sampling with full call stacks (the main one you want)
- `potential-hangs` — detected hangs with timestamps and durations
- `thread-info` — thread metadata
- `time-profile` — alternative time-based profiling (older traces)
- `gcd-perf-event` — GCD performance events

The TOC can be large (environment variables, etc.). Pipe through grep to find what matters:
```bash
xctrace export --input "path.trace" --toc 2>&1 | grep -E '<run number|<table '
```

**Important:** Match `<table ` (with trailing space), NOT `<table schema`. The `schema`
attribute is often not the first attribute on `<table>` elements — xctrace may put
`target-pid`, `high-frequency-sampling`, `needs-kernel-callstack`, `codes`, `callstack`,
or other attributes before `schema`. For example, the cpu-profile table often appears as:
```xml
<table target-pid="SINGLE" high-frequency-sampling="0" schema="cpu-profile" needs-kernel-callstack="0"/>
```
Grepping for `<table schema` would miss this entirely. Always grep for `<table ` to catch
all tables regardless of attribute ordering.

### Step 2: Export hang data first

Hang data is small and immediately actionable:
```bash
xctrace export --input "path.trace" \
  --xpath '/trace-toc/run[@number="1"]/data/table[@schema="potential-hangs"]' \
  --output /tmp/hangs.xml
```

The XML contains rows with `<start-time>`, `<duration>`, and `<hang-type>` (Microhang, Hang,
Severe Hang). Parse these to identify the time ranges where problems occurred. This gives
you the "where to look" before diving into the much larger CPU profile data.

### Step 3: Export CPU profile data

```bash
xctrace export --input "path.trace" \
  --xpath '/trace-toc/run[@number="1"]/data/table[@schema="cpu-profile"]' \
  --output /tmp/cpu_profile.xml
```

These files can be **100MB+**. Never try to read them directly — always use a Python script
to parse and aggregate.

### Step 4: Analyze with Python

The bundled `scripts/analyze_trace.py` script handles parsing. If it's not available or
you need to customize, write a Python script following the patterns below.

## XML Parsing Patterns

### The id/ref deduplication system

xctrace XML uses an id/ref system to avoid repeating data. An element's first occurrence
has an `id` attribute with its full content; subsequent occurrences use `ref` pointing back:

```xml
<!-- First occurrence — has content -->
<thread id="4" fmt="Main Thread 0xf5db59 (MyApp, pid: 78380)">
  <tid id="5" fmt="0xf5db59">16112473</tid>
  ...
</thread>

<!-- Later occurrences — just a ref -->
<thread ref="4"/>
```

**Always build an id cache and resolve refs before reading any element:**

```python
id_cache = {}
for elem in root.iter():
    eid = elem.get('id')
    if eid:
        id_cache[eid] = elem

def resolve(elem):
    if elem is None:
        return None
    ref = elem.get('ref')
    if ref and ref in id_cache:
        return id_cache[ref]
    return elem
```

### Row structure (cpu-profile)

Each `<row>` contains:
- `<sample-time>` — nanoseconds since trace start (divide by 1e9 for seconds)
- `<thread>` — which thread this sample was on (check `fmt` for "Main Thread")
- `<cycle-weight>` — CPU cycles consumed (for weighting samples)
- `<backtrace>` — list of `<frame>` elements (first = leaf/deepest, last = root)

Each `<frame>` has a `name` attribute (the function name) and a `<binary>` child
identifying the library.

## Analysis Dimensions

When analyzing CPU profile data, produce these views:

### 1. Thread breakdown
Count samples per thread to see which threads are busy. The main thread dominating
(>70%) during interactive use is a red flag.

### 2. Leaf functions (self time)
The deepest frame in each backtrace — where the CPU is actually executing. System
allocator functions (`_xzm_free`, `_xzm_xzone_malloc_tiny`) appearing at the top usually
indicate heavy allocation churn in the callers above them, not that malloc itself is the
problem.

### 3. Inclusive functions (on-stack time)
Every unique function that appears anywhere in the backtrace. This shows which high-level
functions are responsible for the most work. Filter aggressively for application-specific
functions — framework functions (`QEventLoop::processEvents`, `CFRunLoopRun`, etc.) will
dominate the raw list and aren't actionable.

### 4. Time-range filtering
Use hang timestamps from Step 2 to filter CPU samples to just the problematic periods.
This is the most powerful technique — it turns "the app is slow" into "during this 5-second
hang, 66% of main thread time was in FunctionX → FunctionY → FunctionZ."

### 5. Lock/mutex detection
Search frame names for: `mutex`, `lock`, `pthread_mutex`, `QMutex`, `QReadWriteLock`,
`QWaitCondition`, `semaphore`, `futex`. High counts on the main thread indicate contention.

### 6. Call stack aggregation
During hang periods, group identical call stacks and count occurrences. The most frequent
stack pattern is your root cause. Show stacks filtered to application-specific frames for
readability.

## Multi-Run Comparison

Instruments supports multiple recording runs in a single `.trace` file (run numbers 1, 2,
3, ...). This is powerful for A/B comparisons:

- Run 1: with feature X enabled
- Run 2: with feature X disabled
- Run 3: baseline (idle/minimal interaction)

Export and analyze each run separately, then compare the same metrics across runs.
Differences in hang counts, thread distributions, or hot functions directly isolate the
variable being tested.

## Practical Tips

1. **Start with hangs** — they're small, fast to parse, and tell you exactly when problems
   occurred. Use those timestamps to focus your CPU profile analysis.

2. **Main thread vs all threads** — always analyze the main thread separately. UI
   responsiveness issues live on the main thread; background work is usually fine.

3. **Filter for your app** — framework/system functions dominate raw inclusive lists.
   Filter for your app's namespace, class names, or binary to see what matters.

4. **Categorize hang causes:**
   - **CPU-bound**: main thread doing heavy computation (the profiler shows your code
     actively running). Fix: move work off the main thread or optimize the algorithm.
   - **Lock contention**: main thread blocked on a mutex held by another thread.
     Fix: reduce lock scope or use lock-free patterns.
   - **Synchronous I/O**: main thread blocked on file/network I/O.
     Fix: make I/O async.

5. **Allocation pressure** — when `_xzm_free` / `_xzm_xzone_malloc_tiny` are top leaf
   functions (>10% combined), the code above them is creating and destroying too many
   temporary objects per frame. Look at the callers.

6. **Don't forget `sample`** — if the user doesn't have a trace file but can reproduce
   the issue, `sample <pid> 5 -f /tmp/sample.txt` captures 5 seconds of call stacks
   from a running process with zero setup.

## Capturing a New Trace (if user doesn't have one yet)

### Quick sampling with `sample`
```bash
# Sample process for 5 seconds
sample <pid> 5 -f /tmp/sample_output.txt
```
The output is a text file with aggregated call stacks — readable directly.

### Using xctrace to record
```bash
# Record CPU profile for an app
xctrace record --template "CPU Profiler" --attach <pid> --output /tmp/recording.trace
# Stop with Ctrl+C
```

### Using spindump for hangs
```bash
# Capture a spindump (requires root for other users' processes)
sudo spindump <pid> 5 -o /tmp/spindump.txt
```
