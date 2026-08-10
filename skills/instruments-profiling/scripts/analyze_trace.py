#!/usr/bin/env python3
"""
Analyze xctrace CPU profile XML exports.

Usage:
    python analyze_trace.py <cpu_profile.xml> [options]

Options:
    --main-thread-only    Only analyze main thread samples
    --time-range START END  Filter to time range in seconds (e.g., --time-range 17.0 28.0)
    --app-filter KEYWORD    Filter inclusive functions by keyword (e.g., --app-filter "MyApp")
    --top N                 Number of top functions to show (default: 30)
    --hang-file PATH        Also parse a potential-hangs XML and show hang periods

Examples:
    # Basic analysis of main thread
    python analyze_trace.py /tmp/cpu_profile.xml --main-thread-only

    # Focus on a specific hang period
    python analyze_trace.py /tmp/cpu_profile.xml --main-thread-only --time-range 17.0 28.0

    # Filter for app-specific functions
    python analyze_trace.py /tmp/cpu_profile.xml --main-thread-only --app-filter "ACE"

    # Full analysis with hang correlation
    python analyze_trace.py /tmp/cpu_profile.xml --main-thread-only --hang-file /tmp/hangs.xml
"""

import xml.etree.ElementTree as ET
import argparse
import sys
from collections import defaultdict


def parse_hangs(filepath):
    """Parse potential-hangs XML and return list of (start_sec, duration_sec, type)."""
    tree = ET.parse(filepath)
    root = tree.getroot()

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

    hangs = []
    for row in root.iter('row'):
        start_elem = row.find('start-time')
        dur_elem = row.find('duration')
        type_elem = resolve(row.find('hang-type'))

        if start_elem is None or dur_elem is None:
            continue

        start_ns = int(start_elem.text) if start_elem.text else 0
        dur_ns = int(dur_elem.text) if dur_elem.text else 0
        hang_type = type_elem.get('fmt', 'Unknown') if type_elem is not None else 'Unknown'

        hangs.append((start_ns / 1e9, dur_ns / 1e9, hang_type))

    return hangs


def analyze(filepath, main_thread_only=False, time_range=None, app_filter=None,
            top_n=30, hangs=None):
    tree = ET.parse(filepath)
    root = tree.getroot()

    # Build id cache for ref resolution
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

    # Counters
    leaf_samples = defaultdict(int)
    leaf_weights = defaultdict(int)
    inclusive_samples = defaultdict(int)
    thread_samples = defaultdict(int)
    lock_samples = defaultdict(int)

    # Per-hang-period counters
    hang_leaf = defaultdict(lambda: defaultdict(int))
    hang_inclusive = defaultdict(lambda: defaultdict(int))
    hang_stacks = defaultdict(list)
    hang_totals = defaultdict(int)

    total_samples = 0
    main_samples = 0

    for row in root.iter('row'):
        # Parse thread
        thread_elem = resolve(row.find('thread'))
        if thread_elem is None:
            continue
        thread_fmt = thread_elem.get('fmt', '')
        is_main = 'Main Thread' in thread_fmt

        # Parse time
        sample_time_elem = row.find('sample-time')
        if sample_time_elem is None:
            continue
        time_ns = int(sample_time_elem.text) if sample_time_elem.text else 0
        time_sec = time_ns / 1e9

        # Time range filter
        if time_range and not (time_range[0] <= time_sec <= time_range[1]):
            continue

        total_samples += 1
        if is_main:
            main_samples += 1

        # Thread breakdown
        thread_short = thread_fmt.split('(')[0].strip() if thread_fmt else 'unknown'
        thread_samples[thread_short] += 1

        if main_thread_only and not is_main:
            continue

        # Parse backtrace
        bt = row.find('backtrace')
        if bt is None:
            continue

        frames = bt.findall('frame')
        if not frames:
            continue

        # Resolve frame names
        frame_names = []
        for f in frames:
            rf = resolve(f)
            name = rf.get('name', '???') if rf is not None else '???'
            frame_names.append(name)

        # Parse weight
        weight_elem = resolve(row.find('cycle-weight'))
        weight = 0
        if weight_elem is not None:
            try:
                weight = int(weight_elem.text or '0')
            except ValueError:
                weight = 0

        # Leaf (self time)
        leaf = frame_names[0]
        leaf_samples[leaf] += 1
        leaf_weights[leaf] += weight

        # Inclusive (on-stack)
        seen = set()
        for name in frame_names:
            if name not in seen:
                inclusive_samples[name] += 1
                seen.add(name)

        # Lock/mutex detection
        for name in frame_names:
            lower = name.lower()
            if any(k in lower for k in ['mutex', 'lock', 'semaphore', 'futex',
                                         'qmutex', 'qreadwrite', 'qwaitcondition']):
                lock_samples[name] += 1

        # Hang period correlation
        if hangs:
            for start, dur, htype in hangs:
                end = start + dur
                if start <= time_sec <= end:
                    key = f"{htype} at {start:.1f}s ({dur:.1f}s)"
                    hang_totals[key] += 1
                    hang_leaf[key][leaf] += 1
                    for name in frame_names:
                        hang_inclusive[key][name] += 1
                    # Collect app-specific stacks
                    if len(hang_stacks[key]) < 100:
                        if app_filter:
                            filtered = [n for n in frame_names if app_filter in n]
                        else:
                            filtered = frame_names[:8]
                        if filtered:
                            hang_stacks[key].append(tuple(filtered[:10]))

    # --- Output ---
    scope_total = main_samples if main_thread_only else total_samples
    scope_label = "MAIN THREAD" if main_thread_only else "ALL THREADS"

    print(f"Total samples: {total_samples}, Main thread: {main_samples}")
    if time_range:
        print(f"Time range filter: {time_range[0]:.1f}s - {time_range[1]:.1f}s")
    print(f"Scope: {scope_label} ({scope_total} samples)")

    # Thread breakdown
    print(f"\n--- Thread Breakdown ---")
    for thread, count in sorted(thread_samples.items(), key=lambda x: -x[1])[:15]:
        pct = count / total_samples * 100
        print(f"  {count:6d} ({pct:5.1f}%) {thread}")

    # Leaf functions
    print(f"\n--- Top Leaf Functions (Self Time, {scope_label}) ---")
    for func, count in sorted(leaf_samples.items(), key=lambda x: -x[1])[:top_n]:
        pct = count / scope_total * 100 if scope_total > 0 else 0
        print(f"  {count:6d} ({pct:5.1f}%) {func[:130]}")

    # Inclusive functions (optionally filtered)
    if app_filter:
        filtered_inc = {k: v for k, v in inclusive_samples.items() if app_filter in k}
        print(f"\n--- Top App Functions (Inclusive, filter: '{app_filter}') ---")
    else:
        filtered_inc = inclusive_samples
        print(f"\n--- Top Inclusive Functions ({scope_label}) ---")

    for func, count in sorted(filtered_inc.items(), key=lambda x: -x[1])[:top_n]:
        pct = count / scope_total * 100 if scope_total > 0 else 0
        print(f"  {count:6d} ({pct:5.1f}%) {func[:130]}")

    # Lock/mutex
    if lock_samples:
        print(f"\n--- Lock/Mutex Related ---")
        for func, count in sorted(lock_samples.items(), key=lambda x: -x[1])[:15]:
            pct = count / scope_total * 100 if scope_total > 0 else 0
            print(f"  {count:6d} ({pct:5.1f}%) {func[:130]}")

    # Hang period correlation
    if hangs and hang_totals:
        for key in sorted(hang_totals.keys()):
            ht = hang_totals[key]
            print(f"\n--- [{key}] {ht} samples ---")

            print(f"  Leaf functions:")
            for func, count in sorted(hang_leaf[key].items(), key=lambda x: -x[1])[:15]:
                pct = count / ht * 100
                print(f"    {count:6d} ({pct:5.1f}%) {func[:120]}")

            if app_filter:
                app_inc = {k: v for k, v in hang_inclusive[key].items() if app_filter in k}
                if app_inc:
                    print(f"  App inclusive functions:")
                    for func, count in sorted(app_inc.items(), key=lambda x: -x[1])[:15]:
                        pct = count / ht * 100
                        print(f"    {count:6d} ({pct:5.1f}%) {func[:120]}")

            if key in hang_stacks:
                stack_counts = defaultdict(int)
                for s in hang_stacks[key]:
                    stack_counts[s] += 1
                print(f"  Top call stacks:")
                for stack, count in sorted(stack_counts.items(), key=lambda x: -x[1])[:10]:
                    print(f"    [{count:3d}x] {' <- '.join(s[:80] for s in stack)}")


def main():
    parser = argparse.ArgumentParser(description='Analyze xctrace CPU profile XML exports')
    parser.add_argument('input', help='Path to CPU profile XML file')
    parser.add_argument('--main-thread-only', action='store_true',
                        help='Only analyze main thread samples')
    parser.add_argument('--time-range', nargs=2, type=float, metavar=('START', 'END'),
                        help='Filter to time range in seconds')
    parser.add_argument('--app-filter', type=str,
                        help='Filter inclusive functions by keyword')
    parser.add_argument('--top', type=int, default=30,
                        help='Number of top functions to show (default: 30)')
    parser.add_argument('--hang-file', type=str,
                        help='Path to potential-hangs XML for correlation')

    args = parser.parse_args()

    hangs = None
    if args.hang_file:
        hangs = parse_hangs(args.hang_file)
        print(f"Loaded {len(hangs)} hang periods:")
        for start, dur, htype in hangs:
            print(f"  {start:8.3f}s  {dur:8.3f}s  {htype}")
        print()

    analyze(
        args.input,
        main_thread_only=args.main_thread_only,
        time_range=tuple(args.time_range) if args.time_range else None,
        app_filter=args.app_filter,
        top_n=args.top,
        hangs=hangs,
    )


if __name__ == '__main__':
    main()
