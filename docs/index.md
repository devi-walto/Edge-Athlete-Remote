# Edge Athlete — Developer Docs

How this system was built, why it is the way it is, and how to work on it day to day. Written for whoever picks it up next.

Most documentation tells you what the code does. You can get that from the code. These docs are for the part you can't: the decisions, what was tried and dropped, and the reasons that stop being obvious a month later. And, separately, the things you look up again and again.

## Pick your path

**New here? About an hour.**

1. {doc}`orientation` (20 min). What the system is, the four kinds of device, how one rep travels from the bar to a screen. Everything else assumes it.
2. **One Journal page** (20 min), for whatever you're about to touch.
3. {doc}`handbook/guides/local-install` (20 min). Get it running. Reading about it is no substitute for watching a rep land on a screen.

**Already working on it?** Go straight to the {doc}`Handbook <handbook/index>`.

## How it's organised

**{doc}`Handbook <handbook/index>`: "how do I…" and "what exactly is…"**
: The pages you come back to. **Guides** walk through a task: set up a local install, run the remote server, change the database. **Reference** is for looking things up: `eactl`, the API, the database tables, the message contract.

**{doc}`Journal <journal/index>`: "why is it like this?"**
: The decisions, read once, in order. **Timeline** is what happened, **Stack** is what it's built with and why, and **Core** is the decisions both installs stand on, with **Local only** and **Remote** as its children.

**{doc}`About <about/index>`**
: The directed study this work was part of, the original build spec, and how these docs are built.

## How a decision is written

Every Journal page follows the same shape:

1. **The problem** I set out to solve.
2. **Try 1, Try 2, …** in order, for the designs that mattered: what worked, and why I moved on.
3. **Where I landed**, and why it fixes what the others couldn't.
4. **Things I passed on**, and **what it cost**.

Tool and library changes are always named: the old one, what it blocked, and what replaced it. A decision written down without what it replaced won't stop the next person from walking back into it.

```{toctree}
:maxdepth: 2
:hidden:

orientation
handbook/index
journal/index
about/index
```
