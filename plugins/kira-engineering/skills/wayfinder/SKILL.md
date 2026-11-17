---
name: wayfinder
description: Chart a huge chunk of work — more than one agent session can hold — as a shared map on your issue tracker, of decision tickets that find the way and stages that land the work once their decisions close, and resolve them one at a time until the destination is reached.
disable-model-invocation: true
---

A loose idea has arrived — too big for one agent session, and wrapped in fog: the way from here to the **destination** isn't visible yet. Wayfinding is about finding that way, not charging at the destination. This skill charts the way as a **shared map** on the repo's issue tracker, then works its tickets one at a time: **decision tickets** — questions whose resolution is a decision, not slices of a build to execute — and, where the destination is a landed change, **stages** — the units of work that land it, each reached once the decisions it needs have closed.

The destination varies per effort, and naming it is the first act of charting — it shapes every ticket. The map is domain-agnostic — engineering work, course content, whatever fits the shape. The destination also sets the map's kind:

- **Planning map** — the destination is a spec to hand off and iterate on, or a decision to lock before planning starts. Every ticket is a decision ticket; the map is done when the way is clear.
- **Execution map** — the destination is a change landed, like a data-structure migration or a rewrite. Decision tickets find the way and **stages** walk it; the map is done when its last stage lands.

## Decide before you do

A decision ticket only decides: it produces a decision, not a deliverable. The pull to just do the work is the signal you've reached the edge of what's decided. On a planning map that edge is the destination — nothing left to decide before someone goes and does the thing, so hand off. On an execution map the doing happens in a **stage**, and only once the decisions blocking it have closed; feeling that pull inside a decision ticket means the stage is missing or still blocked.

## Refer by name

Every map and ticket is an issue, so it has a **name** — its title. In everything the human reads — narration, the map's Decisions-so-far — refer to it by that name, never by a bare id, number, or slug. A wall of `#42, #43, #44` is illegible; names read at a glance. The id and URL don't vanish — a name wraps its link — but they ride _inside_ the name, never stand in for it.

## The Map

The map is a single issue on this repo's issue tracker, labelled `wayfinder:map` — the canonical artifact. Its tickets, and its sub-maps if it has any (see [Sub-maps](#sub-maps)), are child issues of the map.

The map is an **index**, not a store. It lists the decisions made and points at the tickets that hold their detail; a decision lives in exactly one place — its ticket — so the map never restates it, only gists it and links.

**Where the map, its child tickets, blocking, and frontier queries physically live is tracker-specific.** The issue tracker should have been provided to you. If not, tell the user to run `/setup-matt-pocock-skills`. Consult the tracker doc's "Wayfinding operations" section for how _this_ repo expresses them. If no tracker has been provided, default to the local-markdown tracker.

### The map body

The whole map at low resolution, loaded once per session. Open tickets are **not** listed — they are open child issues, found by query.

```markdown
## Destination

<what reaching the end of this map looks like — the spec, decision, or change this effort is finding its way to. One or two lines; every session orients to it before choosing a ticket.>

## Notes

<domain; skills every session should consult; standing preferences for this effort>

## Sub-maps

<!-- umbrella maps only, see "Sub-maps": one line per sub-map, in priority order -->

- [<sub-map title>](link) — <its part of the destination>

## Decisions so far

<!-- the index — one line per closed decision ticket: enough to judge relevance, then zoom the link for the detail the ticket holds -->

- [<closed ticket title>](link) — <one-line gist of the answer>

## Not yet specified

<!-- see "Fog of war": in-scope fog you can't ticket yet; graduates as the frontier advances -->

## Out of scope

<!-- see "Out of scope": work ruled beyond the destination; closed, never graduates -->
```

### Tickets

Each ticket is a **child issue** of the map; the tracker's issue id is its identity. Its body is the question — for a decision ticket, sized to one 100K token agent session; for a stage, the work it lands, sized when the stage is assessed (see [Stages](#stages)):

```markdown
## Question

<the decision or investigation this ticket resolves, or the work this stage lands and when it is done>
```

Each ticket carries a `wayfinder:<type>` label — one of `research`, `prototype`, `grilling`, `task`, `stage` (see [Ticket Types](#ticket-types)).

A session **claims** a ticket by assigning it to the dev driving the map, **first**, before any work, so concurrent sessions skip it. That assignee _is_ the claim: an open, unassigned ticket is unclaimed.

Blocking uses the tracker's **native** dependency relationship — essential because it renders the frontier _visually_ in the tracker's own UI, so the human sees what's takeable without opening the map. Only a tracker that lacks native blocking falls back to a body convention. A ticket is **unblocked** when every ticket blocking it is closed; the **frontier** is the open, unblocked, unclaimed child tickets — the edge of the known.

The answer isn't part of the body — it's recorded on resolution (see [Work through the map](#work-through-the-map)). Assets created while resolving a ticket are linked from the issue, not pasted in.

## Ticket Types

Four types are decision tickets. Each is either **HITL** — human in the loop, worked _with_ a human who speaks for themselves — or **AFK**, driven by the agent alone. A HITL ticket only resolves through that live exchange; the agent never stands in for the human's side of it (a grilling agent that answers its own questions has broken this).

- **Research** (AFK): Reading documentation, third-party APIs, or local resources like knowledge bases to surface a fact a decision waits on. Resolved by a subagent that calls the Skill tool with "research". Use when knowledge outside the current working directory is required.
- **Prototype** (HITL): Raise the fidelity of the discussion by making a cheap, rough, concrete artifact to react to — an outline, a rough take, a stub, or UI/logic code — by calling the Skill tool with "prototype". Links the prototype as an asset. Use when "how should it look" or "how should it behave" is the key question.
- **Grilling** (HITL): Conversation. The default case. Always call the Skill tool twice, for "grilling" and "domain-modeling".
- **Task** (HITL or AFK): Manual work that must happen before a _decision_ can be made — nothing to decide, prototype, or research, but the discussion is blocked until it's done. Signing up for a service so its API can be judged, provisioning access, moving data so its shape can be seen. A task _does_ rather than decides, and it earns its place by unblocking a decision; work that delivers the destination is a stage. The agent drives it alone where it can (AFK); otherwise it hands the human a precise checklist (HITL). Resolved when the work is done; the answer records what was done and any resulting facts (credentials location, new URLs, row counts) later tickets depend on.

The fifth type, **Stage**, is execution: work that lands part of the destination on an execution map. See [Stages](#stages).

## Stages

A **stage** is a unit of execution: it lands part of the destination and leaves the trunk healthy behind it. Its blockers are exactly the decisions it needs, so it reaches the frontier as soon as they close — the map only has to be drilled through for that part, not for the whole destination. A stage you can name precisely is a ticket from the start, blocked by those decisions; the [fog-or-ticket test](#fog-of-war) applies to it as to any ticket.

### Assessing a stage

After claiming a stage, gather what it stands on, as for any ticket: the resolutions of its blockers, the skills the `## Notes` block names, the code it touches. Then **assess** it — one of three outcomes:

- **Not ready** — what's decided leaves gaps. Tell the user it isn't ready, and name the gaps.
  - Gaps that are only conversation, and small enough to leave room in this session for the stage itself: grill them now — call the Skill tool twice, for "grilling" and "domain-modeling" — then assess again. Their answers travel into the spec or brief.
  - Gaps that need research, a prototype or a task, or whose answer other tickets also wait on: file each as a decision ticket blocking the stage, so its answer earns a line in Decisions-so-far. Unassign the stage and stop; the user works those first and returns to it.
- **Spec** — the stage is more than one slice: `/to-tickets` would cut it into several. It becomes a spec with its slices as sub-issues, implemented later through `implement-spec` or slice by slice. `/to-spec` and `/to-tickets` run only when the user invokes them. If they did for this session, run them, writing the spec over the stage's own body rather than into a new issue. Otherwise tell the user: "This should become a spec — invoke `/to-spec` and `/to-tickets` and I'll write it." A question the spec turns up becomes a new decision ticket blocking the stage.
- **One-shot** — the stage is one slice. Ask the user: "I'd like to make this a `ready-for-agent` ticket and then implement it — what do you think?" On their yes, post an agent brief comment per [AGENT-BRIEF.md](../triage/AGENT-BRIEF.md), add the `ready-for-agent` label, and implement it in this session. A step only a human can do goes into the brief as a checklist item naming them.

A spec'd stage closes when its last slice merges; a one-shot stage closes when its work merges. A stage adds no line to Decisions-so-far: the decisions it stands on are already indexed there.

## Sub-maps

When the destination splits into **parts**, each with its own decisions and stages and big enough that one map's Decisions-so-far would stop reading at a glance, chart each part as a **sub-map**: a map of its own, filed as a child issue of the **umbrella** map.

- A sub-map's Destination is its part of the umbrella's. Its Notes open with a link to the umbrella, whose Notes apply to it, so a session on a sub-map also loads the umbrella's Destination and Notes.
- A ticket lives on the map whose part it serves. The umbrella keeps the tickets that cross parts: a decision more than one sub-map waits on, or a stage every part builds on. A decision on the umbrella is indexed there only and never repeated on a sub-map.
- Blocking crosses maps freely: a sub-map's stage can be blocked by an umbrella decision or by a sibling sub-map's stage. Hard order between parts goes on those ticket-to-ticket edges. Soft order is the priority order of the umbrella's **Sub-maps** section. A map is not a ticket: it is never claimed, never blocked, and never on its umbrella's frontier.
- A patch of **Not yet specified** that turns out to be a whole part, with fog of its own, graduates into a sub-map instead of a ticket.
- A sub-map closes when its destination is reached, and it adds no Decisions-so-far line to the umbrella, because its decisions are indexed on its own map. The umbrella closes when its own tickets and every sub-map have closed.

## Fog of war

The map is _deliberately_ incomplete: don't chart what you can't yet see. Beyond the live tickets lies the **fog of war** — the dim view of decisions, investigations and stages you can tell are coming but can't yet pin down, because they hang on questions still open. Resolving a ticket clears the fog ahead of it, graduating whatever's now specifiable into fresh tickets — one at a time, until the way to the destination is clear and no tickets remain.

The map's **Not yet specified** section is where that dim view is written down: the suspected question, the area to revisit later. It's the undiscovered frontier _toward_ the destination — everything here is in scope, just not sharp enough to ticket. Write as loosely or as fully as the view allows; it doubles as a signpost for collaborators reading where the effort is headed.

**Fog or ticket?** The test is whether you can state the question precisely now — _not_ whether you can answer it now.

- **Ticket when** the question is already sharp — even if it's blocked and you can't act on it yet.
- **Not yet specified when** you can't yet phrase it that sharply. Don't pre-slice the fog into ticket-sized pieces: it's coarser than a ticket, and one patch may graduate into several tickets, or none, once the frontier reaches it.

**Not yet specified** excludes what's already decided (Decisions so far), what's already a live ticket, and what's out of scope (the next section).

## Out of scope

Fog only ever gathers _toward_ the destination. The destination fixes the scope, so work beyond it is **out of scope** — it isn't fog, and it doesn't belong in **Not yet specified**. It gets its own **Out of scope** section on the map: work you've consciously ruled out of _this_ effort. Scope, not sharpness, lands it here.

Out-of-scope work never graduates — the frontier stops at the destination — so it returns only if the destination is redrawn, and then as a fresh effort, not a resumption.

Ruling something out of scope is a scoping act, not a step on the route. When a ticket that already exists turns out to sit past the destination — mis-scoped in while charting, or exposed by a resolution — **close it** (a closed ticket is unambiguously off the frontier) and leave one line in the **Out of scope** section: the gist plus why it's out of scope, linking the closed ticket. It stays out of **Decisions so far**, which records the route actually walked — a scope boundary isn't a step on it.

## Invocation

Two modes. Either way, **never resolve more than one ticket per session** — with the exception of research tickets. A one-shot stage's implementation is part of resolving that one ticket.

### Chart the map

User invokes with a loose idea.

1. **Name the destination.** Call the Skill tool twice, for "grilling" and "domain-modeling", to pin down what this map is finding its way to — the spec, decision, or change, and with it the map's kind. The destination fixes the scope, so it's settled first.
2. **Map the frontier.** Grill again, **breadth-first** this time: fan out across the whole space rather than deep on any one thread, surfacing the open decisions, the first steps takeable now and, on an execution map, the stages the work lands in. Watch for **parts** that each need their own decisions and stages (see [Sub-maps](#sub-maps)). **If this surfaces no fog** — the way to the destination is already clear, the whole journey small enough for one session — you don't need a map. Stop and ask the user how they'd like to proceed.
3. **Create the map** (label `wayfinder:map`): Destination and Notes filled in, Decisions-so-far empty, the fog sketched into **Not yet specified**. If the space splits into parts, this map is the umbrella: create one sub-map per part as its child, each with its Destination, Notes and fog, and list them in the umbrella's **Sub-maps** section.
4. **Create the tickets you can specify now** as child issues of the map they serve — then wire blocking edges in a **second pass** (issues need ids before they can reference each other). Wiring sorts them into the frontier and the blocked; everything you can't yet specify stays in the fog — the **Not yet specified** section. A part too foggy to ticket keeps a sub-map with only **Not yet specified** filled in.
5. **Fire the research subagents.** For each `research` ticket you just created, spin up a subagent that calls the Skill tool with "research" to resolve it in parallel, capturing its findings on a throwaway `research/<name>` branch with a context pointer from the ticket.
6. Stop — charting is one session's work; it hand-resolves nothing.

### Work through the map

User invokes with a map (URL or number). A ticket is **optional** — without one, you pick the next ticket, not the user.

1. Load the **map** — the low-res view, not every ticket body. For a sub-map, also load its umbrella's Destination and Notes.
2. Choose the ticket. If the user named one, use it. Otherwise take the first frontier ticket in order; when the map's own frontier is empty and it has sub-maps, take the first frontier ticket of the highest-priority sub-map that has one. **Claim it**: assign it to yourself before any work.
3. Resolve it — **zoom as needed**: fetch the full body of any related or closed ticket on demand; call the Skill tool for whichever skills the `## Notes` block names. A stage resolves through its [assessment](#assessing-a-stage). For a decision ticket, if in doubt, call the Skill tool twice, for "grilling" and "domain-modeling".
4. Record the resolution. A decision ticket: post the answer as a **resolution comment**, **close** the issue, and **append a context pointer** to the map's Decisions-so-far. A stage stays open until its work merges (see [Stages](#stages)).
5. Add newly-surfaced tickets (create-then-wire); graduate any fog the answer has made specifiable, clearing each graduated patch from **Not yet specified** so it lives only as its new ticket or sub-map. If the answer reveals a ticket — this one or another — sits beyond the destination, **rule it out of scope** rather than resolving it on the route. If the decision invalidates other parts of the map, update or delete those tickets.

The user may run unblocked tickets in parallel, so expect other sessions to be editing the tracker concurrently.
