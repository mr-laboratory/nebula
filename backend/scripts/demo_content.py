"""Curated demo content: fictional authors, original technology and market posts, and comments."""

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Persona:
    username: str
    display_name: str
    bio: str


@dataclass(frozen=True, slots=True)
class DemoPost:
    author: str  # a Persona username
    title: str
    excerpt: str
    tags: tuple[str, ...]
    content: str
    days_ago: int
    comments: tuple[tuple[str, str], ...] = ()  # (Persona username, body)
    draft: bool = False
    likes: int = 3  # how many other personas like it


TAGS = (
    "ai",
    "cloud",
    "databases",
    "security",
    "semiconductors",
    "fintech",
    "startups",
    "web",
    "devops",
    "markets",
)

PERSONAS = (
    Persona(
        "maya_chen",
        "Maya Chen",
        "Staff engineer writing about AI systems and the unglamorous work of shipping them.",
    ),
    Persona(
        "arjun_rao",
        "Arjun Rao",
        "Cloud architect. FinOps, Kubernetes and the occasional outage review.",
    ),
    Persona(
        "lena_fischer",
        "Lena Fischer",
        "Database engineer. Postgres by day, query plans by night.",
    ),
    Persona(
        "tomas_alvarez",
        "Tomás Álvarez",
        "Security engineer focused on identity, supply chains and incident response.",
    ),
    Persona(
        "priya_nair",
        "Priya Nair",
        "Industry analyst covering chips, fabs and the markets around them.",
    ),
    Persona(
        "daniel_okafor",
        "Daniel Okafor",
        "Product lead in payments. Writing about fintech, regulation and money movement.",
    ),
    Persona(
        "sofia_rossi",
        "Sofia Rossi",
        "Frontend engineer. Web performance, accessibility and design systems.",
    ),
)

POSTS = (
    DemoPost(
        author="maya_chen",
        title="Evaluating LLM features before they reach users",
        excerpt="A demo that works five times in a row is not an evaluation. Here is the "
        "lightweight process we use before any model-backed feature ships.",
        tags=("ai",),
        days_ago=3,
        likes=6,
        content="""\
Every team building with large language models hits the same wall. The prototype is
impressive in a meeting, then real users arrive and find the edges within an hour. The gap
is almost never the model. It is the lack of a repeatable way to say whether a change made
things better or worse.

## Start with a golden set

Collect 50 to 200 real inputs before you write a single prompt. Pull them from support
tickets, search logs or sales calls, and include the awkward ones: typos, mixed languages,
requests the feature should refuse. For each input, write down what a good answer must
contain, not the exact wording.

## Score what matters

We use three layers:

1. **Deterministic checks**: valid JSON, no leaked system prompt, length limits, required
   fields present.
2. **Rubric grading**: a second model grades each answer against the written criteria,
   and we spot-check its grades by hand every week.
3. **Human review**: a small sample of production traffic, read by the people who own the
   feature.

The first layer catches most regressions and costs almost nothing, so it runs on every
commit.

## Treat prompts like code

Prompts live in the repository, change through pull requests, and every pull request shows
the eval score before and after. A prompt tweak that fixes one complaint and quietly breaks
twenty other cases is the most common failure we see, and it is invisible without a
baseline.

> If you can't measure a change, you are not iterating. You are guessing with extra steps.

## Watch it after launch

Log inputs and outcomes (with consent and with personal data removed), and feed the
surprising ones back into the golden set. The set should grow every sprint. Six months in,
it becomes the most valuable asset the feature has, far more durable than any single
prompt.
""",
        comments=(
            (
                "lena_fischer",
                "The golden set point is underrated. We did the same for search relevance "
                "years ago and it changed every conversation from opinions to numbers.",
            ),
            (
                "daniel_okafor",
                "How do you handle cases where graders disagree with each other? We see a lot "
                "of that with anything involving tone.",
            ),
            (
                "maya_chen",
                "We keep those cases and label them as ambiguous. If humans can't agree, the "
                "rubric is usually the problem, so we rewrite it rather than the prompt.",
            ),
        ),
    ),
    DemoPost(
        author="maya_chen",
        title="Retrieval-augmented generation is a search problem first",
        excerpt="Most disappointing RAG systems have a retrieval problem, not a model problem. "
        "Fix what you fetch before you tune what you generate.",
        tags=("ai", "databases"),
        days_ago=12,
        likes=5,
        content="""\
Retrieval-augmented generation sounds like a model technique, but most of the engineering
lives in the retrieval half. If the right passage never reaches the prompt, no amount of
prompt engineering will produce the right answer.

## Measure retrieval on its own

Before looking at generated answers, check whether the relevant document appears in the top
results. Recall at 5 or 10 on a labelled set of questions tells you more than any end-to-end
demo. When recall is low, the answers will be confidently wrong, which is worse than no
answer at all.

## Chunking decides a lot

Splitting documents into fixed-size pieces is the default, and it often cuts a table away
from its heading or an answer away from its question. Chunk along the structure the
document already has: sections, headings, list items. Keep the section title with each
chunk so it still makes sense on its own.

## Hybrid search beats either half

Dense embeddings are good at meaning and bad at exact terms such as product codes, error
messages and names. Keyword search is the opposite. Combining both, then reranking the
merged list, is a reliable improvement in almost every domain we have tried.

| Query type | Keyword search | Embeddings |
| --- | --- | --- |
| Error code `E4012` | Strong | Weak |
| "Why is my invoice late?" | Weak | Strong |
| Product name plus intent | Good | Good |

## Keep the database boring

You probably don't need a new database. Many teams store embeddings next to the source rows
in Postgres with an extension such as pgvector, which keeps permissions, deletes and
backups in one place. Specialised vector stores make sense at large scale, but start where
your data already lives.

The best RAG systems we have seen look less like AI projects and more like good search
teams with a model at the end of the pipeline.
""",
        comments=(
            (
                "lena_fischer",
                "Thank you for the pgvector mention. Keeping deletes consistent is the part "
                "people forget until a customer asks for their data to be removed.",
            ),
            (
                "sofia_rossi",
                "The table makes this click. We had exactly the error-code problem in our "
                "docs search.",
            ),
        ),
    ),
    DemoPost(
        author="arjun_rao",
        title="Reading your cloud bill like an engineer",
        excerpt="Cloud costs rarely explode from one bad decision. They drift, line by line. "
        "A monthly habit that keeps the drift visible.",
        tags=("cloud", "devops"),
        days_ago=5,
        likes=5,
        content="""\
The cloud bill is the one report every engineering team receives and almost nobody reads.
Finance sees the total, engineers see nothing, and the gap between the two is where money
disappears.

## Tag first, then talk

You can't discuss cost without knowing who owns it. Enforce a small set of tags on every
resource: `team`, `service` and `environment`. Block untagged resources in your
infrastructure pipeline rather than cleaning them up later. Once costs are grouped by
service, the conversation changes from "the cloud is expensive" to "this service costs more
than it earns".

## The usual suspects

In our reviews, the same items show up again and again:

- Development environments running around the clock
- Unattached disks and old snapshots nobody remembers creating
- Data transfer between regions or availability zones
- Log retention set to "forever" by default
- Oversized instances chosen during a launch and never revisited

None of these are exotic. They are simply invisible until someone looks.

## Commitments are a finance tool

Reserved capacity and savings plans can cut compute costs significantly, but they lock you
in. Buy them for the steady baseline you are confident about, and leave the spiky part on
demand. Revisit the baseline every quarter.

## Make it a habit

Once a month, each team spends thirty minutes on its own costs: the top five line items,
the biggest change since last month, and one action. Put the unit cost on a dashboard, such
as cost per thousand requests or per active customer. A rising total is fine when the
business is growing. A rising unit cost is the real warning sign.
""",
        comments=(
            (
                "daniel_okafor",
                "Unit cost per customer was a turning point for us too. It made the "
                "conversation with finance far less tense.",
            ),
            (
                "tomas_alvarez",
                "Blocking untagged resources also helps security. Orphaned resources are "
                "exactly the ones nobody patches.",
            ),
            (
                "maya_chen",
                "Log retention bit us last year. We were storing debug logs for a service we "
                "had already shut down.",
            ),
        ),
    ),
    DemoPost(
        author="arjun_rao",
        title="Kubernetes is not a deployment strategy",
        excerpt="Kubernetes answers how containers run. It doesn't answer how changes reach "
        "users safely. That part is still yours.",
        tags=("devops", "cloud"),
        days_ago=20,
        likes=4,
        content="""\
Teams often move to Kubernetes expecting safer releases. What they get is a very capable
scheduler. Safe releases still depend on decisions the platform can't make for you.

## Rolling updates are only the start

The default rolling update replaces pods gradually, which prevents total downtime. It
doesn't check whether the new version is actually working. Without meaningful readiness
probes, a broken release rolls out just as smoothly as a good one.

```yaml
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  periodSeconds: 5
  failureThreshold: 3
```

A readiness endpoint should check what the service needs to do useful work, such as its
database connection, not merely that the process is alive.

## Decide how you roll back

Rolling back a deployment is easy. Rolling back a database migration is not. We follow two
rules:

1. Migrations are backwards compatible with the previous release.
2. Destructive changes, such as dropping a column, ship one release later than the code that
   stopped using it.

With those rules, rolling back is always a single command.

## Canary when the risk is real

For high-traffic services, send a small share of requests to the new version first and
compare error rates and latency against the old one. Tools can automate this, but even a
manual canary with a clear checklist beats a full rollout on a Friday afternoon.

## The boring conclusion

Kubernetes gives you building blocks. The strategy is the combination of probes, backwards
compatible changes, gradual exposure and the discipline to stop when the numbers look wrong.
""",
        comments=(
            (
                "lena_fischer",
                "Rule two has saved us more than once. Dropping a column in the same release "
                "is how you learn about rollbacks the hard way.",
            ),
            (
                "sofia_rossi",
                "Would love a follow-up on how you run canaries without a service mesh.",
            ),
        ),
    ),
    DemoPost(
        author="arjun_rao",
        title="What a good incident review looks like",
        excerpt="Notes for a template our team is testing. The goal is learning, not blame, "
        "and a short list of actions someone actually owns.",
        tags=("devops",),
        days_ago=1,
        draft=True,
        content="""\
Draft: notes for the incident review template.

## Sections

- **Summary**: two sentences a non-engineer can understand
- **Impact**: who was affected, for how long, and how we know
- **Timeline**: detection, response and recovery, with timestamps
- **Contributing factors**: plural, never a single root cause
- **What went well**: this section matters as much as the others
- **Actions**: each one with an owner and a date

## Open questions

- Should reviews for small incidents be optional?
- Where do we publish them so other teams actually read them?
""",
    ),
    DemoPost(
        author="lena_fischer",
        title="Why your Postgres index isn't being used",
        excerpt="You added the index, the query is still slow, and EXPLAIN shows a sequential "
        "scan. Five common reasons and how to check each one.",
        tags=("databases",),
        days_ago=8,
        likes=7,
        content="""\
Few things are more frustrating than adding an index and watching the planner ignore it. The
planner isn't being stubborn. It is making a cost-based decision with the information it
has, and usually one of these five things is off.

## 1. The query doesn't match the index

An index on `email` won't help `WHERE lower(email) = $1`. Either index the expression or
change the query so both sides agree:

```sql
CREATE INDEX users_email_lower_idx ON users (lower(email));
```

## 2. The table is small

For a table with a few hundred rows, reading it in one pass is genuinely cheaper than
jumping through an index. This is correct behaviour, and it will change as the table grows.

## 3. The condition matches too many rows

If a filter returns a large share of the table, such as `status = 'published'` when almost
every row is published, a sequential scan wins. Partial indexes help when you query the rare
value:

```sql
CREATE INDEX posts_drafts_idx ON posts (author_id) WHERE status = 'draft';
```

## 4. Statistics are out of date

The planner estimates row counts from statistics collected by `ANALYZE`. After a large bulk
load, run it manually. If `EXPLAIN ANALYZE` shows estimated rows far from actual rows,
stale statistics are the first suspect.

## 5. Column order in a composite index

An index on `(author_id, created_at)` supports filtering by author and sorting by date. It
doesn't help a query that filters only by `created_at`. Put the equality columns first and
the range or sort column last.

## Always measure

Use `EXPLAIN (ANALYZE, BUFFERS)` on realistic data, not an empty development database. The
[PostgreSQL documentation](https://www.postgresql.org/docs/current/using-explain.html) on
reading plans is one of the best investments a backend engineer can make.
""",
        comments=(
            (
                "arjun_rao",
                "Number four is the one I forget every time after a big import. Bookmarking this.",
            ),
            (
                "maya_chen",
                "The partial index example is great. We had the exact published versus draft "
                "situation.",
            ),
            (
                "tomas_alvarez",
                "Clear and practical. More posts like this, please.",
            ),
        ),
    ),
    DemoPost(
        author="lena_fischer",
        title="Connection pooling, explained with a coffee shop",
        excerpt="Why opening a database connection per request hurts, and what a pool "
        "actually does, without a single diagram of TCP handshakes.",
        tags=("databases", "web"),
        days_ago=27,
        likes=4,
        content="""\
Imagine a coffee shop where every customer must hire a new barista, train them, serve one
drink, and then fire them. That is roughly what happens when an application opens a new
database connection for every request.

## Connections are expensive

Each Postgres connection is a separate server process with its own memory. Creating one
involves authentication, and often encryption setup, before the first query runs. Under
load, the cost of opening connections can exceed the cost of the queries themselves.

## A pool keeps baristas on staff

A connection pool opens a fixed number of connections and lends them out. A request borrows
a connection, runs its queries, and returns it. The next request reuses it immediately.

- **Pool size** is how many baristas you employ.
- **Timeout** is how long a customer waits before giving up.
- **Overflow** is the temporary staff you hire during a rush.

## Bigger isn't better

It is tempting to set the pool size to hundreds. But the database has a limited number of
CPU cores, and past a point more connections only means more waiting and context switching.
A small pool that keeps the database busy but not overwhelmed usually gives the best
throughput. Start small, measure, and increase slowly.

## Many app servers, one database

If you run twenty application instances with a pool of twenty each, the database sees four
hundred connections. At that point, a dedicated pooler such as PgBouncer in front of
Postgres lets many clients share a much smaller set of real connections.

The coffee shop analogy holds: a few well-trained baristas with a good queue serve more
customers than a crowd of new hires bumping into each other behind the counter.
""",
        comments=(
            (
                "sofia_rossi",
                "Finally an explanation I can send to the frontend team. Thank you.",
            ),
            (
                "arjun_rao",
                "The twenty instances times twenty connections maths is exactly what happened "
                "to us after enabling autoscaling.",
            ),
        ),
    ),
    DemoPost(
        author="tomas_alvarez",
        title="Passkeys are ready. Are your users?",
        excerpt="Passkeys remove phishing from the login flow, but only if the rollout "
        "respects how people actually use their devices.",
        tags=("security", "web"),
        days_ago=6,
        likes=6,
        content="""\
Passwords fail in predictable ways: reuse, phishing and weak choices. Passkeys, built on the
WebAuthn standard, fix all three. The private key never leaves the user's device, and the
browser only signs challenges for the site that created the key, so a lookalike domain gets
nothing.

## Why now

Every major operating system and browser now supports passkeys, and they sync between
devices through the platform's password manager. That solves the biggest earlier objection:
losing your phone no longer means losing your account.

## Rolling out without locking people out

The technology is ready. The difficult part is the user experience.

1. **Offer, don't force.** Invite users to add a passkey after a successful login, when
   they are already authenticated.
2. **Keep a recovery path.** Email-based recovery or backup codes are still needed for people
   who switch ecosystems.
3. **Name keys clearly.** "iPhone, added in March" is far more useful on a security page
   than a list of identical entries.
4. **Explain it in one sentence.** "Sign in with your fingerprint or face instead of a
   password" works better than any mention of cryptography.

## What stays the same

Passkeys secure the login. They don't secure the session afterwards. Short-lived access
tokens, careful cookie settings and revocation on password or passkey changes still
matter.

## Where to start

Add passkeys as an option for your most security-conscious users, such as administrators,
measure how many adopt them, and watch support tickets closely. The goal is a login that is
both safer and easier, and passkeys are one of the rare changes that can deliver both.
""",
        comments=(
            (
                "sofia_rossi",
                "Naming the keys is such a good point. Our security page was a list of five "
                "entries all called 'Chrome'.",
            ),
            (
                "daniel_okafor",
                "In payments we see the same pattern: offering it after login gets far better "
                "adoption than any banner.",
            ),
            (
                "maya_chen",
                "Do you keep passwords as a fallback forever, or plan to remove them?",
            ),
            (
                "tomas_alvarez",
                "For now we keep them. Removal only makes sense once almost every active "
                "account has a passkey and a working recovery method.",
            ),
        ),
    ),
    DemoPost(
        author="tomas_alvarez",
        title="Software supply chain security, one lockfile at a time",
        excerpt="You didn't write most of the code you ship. A practical checklist for "
        "trusting the dependencies you did choose.",
        tags=("security", "devops"),
        days_ago=15,
        likes=5,
        content="""\
A modern web application pulls in hundreds of open-source packages, most of them indirect.
Attackers have noticed. Typosquatted names, hijacked maintainer accounts and malicious
install scripts are now routine. The good news is that the defences are mostly habits, not
products.

## Pin everything

Commit your lockfile and install from it in continuous integration. A lockfile records the
exact versions and integrity hashes you tested, so a compromised new release can't slip in
silently between your laptop and production.

## Update on purpose

Automated update pull requests keep you current, but review them like any other change. A
patch release that suddenly adds a network call or an install script deserves a closer
look.

## Scan continuously

- Check dependencies against known vulnerability databases on every build.
- Scan commits for accidentally committed secrets before they are pushed.
- Pin third-party CI actions to a full commit hash, not a tag that can be moved.

## Reduce what you depend on

Every dependency is a relationship with strangers. Before adding one, ask whether the
standard library already covers it, whether the package is maintained, and how many
transitive packages it brings along.

## Know what you shipped

Generate a software bill of materials for each release. When the next widely used library
has a critical vulnerability, you want to answer "are we affected?" in minutes rather than
days.

Supply chain security isn't one tool. It is a series of small, boring defaults that make an
attacker's job much harder.
""",
        comments=(
            (
                "arjun_rao",
                "Pinning actions to a commit hash is the one most teams skip. It should be the "
                "default.",
            ),
            (
                "lena_fischer",
                "The question about transitive dependencies is a good filter. Some small "
                "helpers bring in dozens of packages.",
            ),
        ),
    ),
    DemoPost(
        author="priya_nair",
        title="Why advanced packaging matters as much as smaller transistors",
        excerpt="For decades, progress meant shrinking transistors. Now a growing share of "
        "performance gains comes from how chips are put together.",
        tags=("semiconductors",),
        days_ago=4,
        likes=6,
        content="""\
For most of the industry's history, better chips meant smaller transistors. Each new
manufacturing node packed more of them into the same area, and performance followed. That
engine is still running, but it is slower and far more expensive than it used to be. A
growing share of the progress now happens after the silicon is made, in packaging.

## From one die to many

Instead of building one enormous chip, designers increasingly split a product into smaller
pieces, often called chiplets, and connect them inside a single package. Smaller dies have
better manufacturing yields, and each piece can use the process that suits it best: the
newest node for compute, an older and cheaper one for input and output.

## Memory moves closer

AI accelerators are often limited by how fast they can move data, not by how fast they can
calculate. High-bandwidth memory stacks several memory dies vertically and places them right
next to the processor on a shared base, called an interposer. The short, wide connections
deliver far more bandwidth than memory on a separate circuit board.

## Why investors care

Advanced packaging capacity has become a bottleneck in its own right. Companies that
master these techniques, from foundries to specialist assembly and test firms, now sit on
the critical path for AI hardware. When supply of packaging capacity is tight, it can limit
shipments even when enough chips have been manufactured.

## What to watch

- Capacity expansion announcements for advanced packaging
- Standards for connecting chiplets from different vendors
- New materials for substrates and interposers

The next decade of chip performance won't come from a single breakthrough. It will come from
many improvements in how pieces are combined, and packaging is where many of them meet.
""",
        comments=(
            (
                "maya_chen",
                "The memory bandwidth point explains a lot about why our inference costs "
                "didn't fall as fast as raw compute numbers suggested.",
            ),
            (
                "daniel_okafor",
                "Great primer. Would love a follow-up on who the key suppliers are in each step.",
            ),
            (
                "priya_nair",
                "That's the next post. The supply chain is more concentrated than most "
                "people expect.",
            ),
        ),
    ),
    DemoPost(
        author="priya_nair",
        title="How to read a semiconductor earnings call",
        excerpt="Revenue is the headline, but inventory, lead times and capital spending "
        "plans tell you where the cycle is heading.",
        tags=("semiconductors", "markets"),
        days_ago=18,
        likes=4,
        content="""\
The semiconductor industry is famously cyclical. Shortages lead to over-ordering, which
leads to excess inventory, which leads to cuts, which eventually leads to the next shortage.
Earnings calls are where companies reveal, often indirectly, where they think they are in
that loop.

## Look past revenue

Revenue tells you what already happened. For direction, focus on:

- **Inventory days**: rising inventory at chipmakers or their customers often precedes
  weaker orders.
- **Lead times**: long lead times signal tight supply, and shortening lead times can mean
  demand is cooling.
- **Utilisation**: factories running below capacity pressure margins, because fabs have high
  fixed costs.
- **Gross margin guidance**: a sensitive signal of pricing power and factory loading.

## Listen to the customers too

A memory maker's outlook is only half the story. Calls from phone makers, PC vendors, cloud
providers and carmakers tell you whether end demand supports the orders. When suppliers
sound confident and customers sound cautious, something has to give.

## Capital spending is a long bet

Announced spending on new fabs and equipment shapes supply years ahead. Big increases across
the industry at the same time have historically preceded periods of oversupply. Cuts do the
opposite.

## Mind the mix

The industry isn't one market. Chips for AI data centres, cars, phones and industrial
equipment can be in completely different phases at the same time. A strong quarter driven by
one segment can hide weakness in the others, so read the segment breakdown before drawing
conclusions.

This isn't investment advice, just a framework for turning a long call into a few useful
signals.
""",
        comments=(
            (
                "daniel_okafor",
                "Suppliers confident and customers cautious is a great way to frame it.",
            ),
            (
                "arjun_rao",
                "Cloud capital spending comments are now some of the most closely watched "
                "lines in the whole industry.",
            ),
        ),
    ),
    DemoPost(
        author="priya_nair",
        title="The AI infrastructure build-out and what it means for everyone else",
        excerpt="Data centres, power and chips are absorbing record investment. The effects "
        "reach far beyond the companies building AI models.",
        tags=("markets", "ai"),
        days_ago=35,
        likes=5,
        content="""\
The largest technology companies are spending on data centres at a pace the industry hasn't
seen before. Accelerators get the headlines, but the build-out pulls on a long chain of
suppliers, and the effects spread well beyond the AI sector.

## Power is the new constraint

A modern AI data centre needs far more electricity than a traditional one. In several
regions, the waiting time for a new grid connection now shapes where facilities can be
built. Utilities, transformer makers and cooling suppliers have become part of the AI story,
and long-term power agreements are now a strategic asset.

## The supply chain widens

Beyond chips, the build-out needs:

- High-speed networking and optical components
- Liquid cooling systems for dense racks
- Construction, electrical and specialist engineering capacity
- Land close to both power and fibre

Each of these has its own lead times, so a bottleneck in one can delay an entire project.

## What to ask as an investor or an operator

The key question is whether revenue from AI products grows quickly enough to justify the
spending. Watch how companies describe returns: usage growth, pricing, and whether AI
features lift existing products or only add costs. History offers both kinds of example.
Some infrastructure booms produced lasting platforms, while others left expensive capacity
waiting for demand to catch up.

## For everyone else

Smaller companies benefit from falling prices for model access and a steady stream of new
tools. They also compete for the same scarce resources: specialist engineers, cloud
capacity, and sometimes the attention of their own customers.

The build-out is real and physical. Following the power, the cooling and the concrete is
often a clearer guide than following the announcements.
""",
        comments=(
            (
                "arjun_rao",
                "Grid connection timelines are coming up in every capacity planning meeting "
                "I'm part of now.",
            ),
            (
                "maya_chen",
                "Good reminder that inference efficiency work isn't only about cost. It is "
                "about fitting inside a power budget.",
            ),
        ),
    ),
    DemoPost(
        author="daniel_okafor",
        title="Real-time payments change more than speed",
        excerpt="Instant transfers look like a faster version of what we had. In practice, "
        "they change fraud, liquidity and product design.",
        tags=("fintech",),
        days_ago=9,
        likes=5,
        content="""\
Instant payment systems now run in many countries: UPI in India, Pix in Brazil, Faster
Payments in the UK and FedNow in the United States, among others. From the outside, they
look like a speed upgrade. Inside a payments company, they change almost everything.

## Final means final

Card payments can be disputed and reversed for weeks. Most instant payments are
irrevocable within seconds. That shifts fraud prevention from recovering money afterwards
to stopping it beforehand, often in a few hundred milliseconds. Authorised push payment
scams, where a victim is tricked into sending money themselves, have become one of the main
risks.

## Liquidity never sleeps

Batch systems settled on business days. Instant schemes run around the clock, including
weekends and holidays. Treasury teams need to fund settlement accounts continuously, and
banks need real-time visibility of their positions rather than an end-of-day report.

## New products become possible

- Paying freelancers the moment a job is approved
- Insurance payouts sent while the customer is still on the phone
- Merchants accepting payments by QR code without card fees
- Request-to-pay flows that replace some direct debits

## What product teams should get right

Confirmation screens matter more when there is no undo. Showing the recipient's verified
name before sending, adding a short delay for unusual first-time payments, and explaining
clearly why a payment was paused all reduce harm without adding much friction.

Real-time payments aren't just faster rails. They move risk, operations and design decisions
into the same moment, and the companies that treat them that way will build the better
products.
""",
        comments=(
            (
                "tomas_alvarez",
                "The fraud shift from recovery to prevention is exactly the same story as "
                "moving from detection to prevention in security.",
            ),
            (
                "priya_nair",
                "Pix adoption is a fascinating case study. Merchants adopted it faster than "
                "many expected.",
            ),
            (
                "sofia_rossi",
                "Showing the verified recipient name is such a simple UI change with a big effect.",
            ),
        ),
    ),
    DemoPost(
        author="daniel_okafor",
        title="Unit economics before growth: lessons from fintech startups",
        excerpt="Cheap capital hid a lot of weak business models. The fintech companies that "
        "lasted knew what each customer earned and cost.",
        tags=("startups", "fintech", "markets"),
        days_ago=24,
        likes=4,
        content="""\
When funding was plentiful, many fintech startups grew by paying for customers and hoping
the economics would work out later. When funding tightened, the difference between growth
and a business became obvious very quickly.

## Know your numbers per customer

Three numbers explain most fintech businesses:

| Metric | Question it answers |
| --- | --- |
| Customer acquisition cost | What do we pay to win one customer? |
| Contribution margin | What does a customer earn after direct costs? |
| Payback period | How many months until acquisition cost is recovered? |

If payback takes longer than customers typically stay, growth makes the problem bigger, not
smaller.

## Direct costs hide in payments

Interchange, processing fees, fraud losses, compliance checks and customer support all scale
with usage. A product with thin fees can lose money on every transaction once these are
included. Model them per transaction and per customer, not only as a total.

## Interest rates change the model

Some business models earn most of their revenue from interest on customer balances. That
income rises and falls with central bank rates, which is outside the company's control.
Strong teams plan for both scenarios and avoid treating a high-rate year as the new normal.

## Growth that compounds

The durable companies we have seen grow through products customers use every week, low
support costs, and referrals rather than paid acquisition. They add revenue streams, such
as business accounts or lending, only after the core product pays for itself.

Growth is still the goal. It just works best when each new customer makes the business
stronger rather than simply bigger.
""",
        comments=(
            (
                "priya_nair",
                "The interest rate point is so important. A lot of reported profitability "
                "turned out to be a rate cycle.",
            ),
            (
                "arjun_rao",
                "This applies to infrastructure costs too. Cloud spend per customer belongs in "
                "the same table.",
            ),
        ),
    ),
    DemoPost(
        author="sofia_rossi",
        title="Core Web Vitals in plain language",
        excerpt="Three numbers describe how a page feels to a real person: how fast it "
        "appears, how quickly it responds, and whether it jumps around.",
        tags=("web",),
        days_ago=2,
        likes=6,
        content="""\
Core Web Vitals are a set of measurements that describe how a page feels to someone using
it. Search engines use them as a ranking signal, but the better reason to care is that they
map closely to user frustration.

## The three vitals

- **Largest Contentful Paint (LCP)**: how long until the main content, usually a hero image
  or headline, is visible. Aim for 2.5 seconds or less.
- **Interaction to Next Paint (INP)**: how quickly the page responds after a click, tap or
  key press. Aim for 200 milliseconds or less. It replaced First Input Delay in 2024.
- **Cumulative Layout Shift (CLS)**: how much the content jumps around while loading. Aim
  for 0.1 or less.

## Quick wins for each

For **LCP**, make the main image discoverable early, serve it in a modern format at the
right size, and avoid loading it lazily when it is visible straight away.

For **INP**, break up long JavaScript tasks, defer work that isn't needed for the first
interaction, and be careful with heavy third-party scripts.

For **CLS**, reserve space for images and embeds with width and height or an aspect ratio,
and don't insert banners above content that is already visible.

```html
<img src="/cover.webp" width="1200" height="630" alt="Team planning board" />
```

## Measure real users

Lab tools are useful for debugging, but real-user data tells you what people actually
experience on slower phones and networks. Look at the 75th percentile, not the average, since
that is where frustration shows up.

Good vitals won't rescue a confusing product, but poor ones can quietly undo good design.
""",
        comments=(
            (
                "lena_fischer",
                "The 75th percentile point applies to databases too. Averages hide exactly the "
                "users who are suffering.",
            ),
            (
                "tomas_alvarez",
                "Third-party scripts are also a security concern. Fewer of them helps both.",
            ),
            (
                "maya_chen",
                "Clear and short. Sharing with our product managers.",
            ),
        ),
    ),
    DemoPost(
        author="sofia_rossi",
        title="Accessibility is a performance feature",
        excerpt="Working notes on why accessible interfaces also tend to be faster, simpler "
        "and easier to maintain.",
        tags=("web",),
        days_ago=1,
        draft=True,
        content="""\
Working notes, not ready yet.

## Points to cover

- Semantic HTML ships less JavaScript than custom widgets.
- Visible focus states help keyboard users and power users alike.
- Respecting reduced motion also saves battery.
- Good contrast helps everyone reading outdoors.

## Examples to find

- A custom dropdown replaced by a native select
- A modal rebuilt with the dialog element
""",
    ),
)


_BLOCK_START = re.compile(r"^(#|>|\||```|- |\d+\. )")


def unwrap(markdown: str) -> str:
    """Join the hard-wrapped lines above into paragraphs, as an author would type them."""
    lines: list[str] = []
    in_fence = False
    for line in markdown.split("\n"):
        if line.startswith("```"):
            in_fence = not in_fence
        elif not in_fence and line and lines and lines[-1] and not _BLOCK_START.match(line):
            previous = lines[-1]
            if not previous.startswith(("#", "|", "```")):
                lines[-1] = f"{previous} {line.strip()}"
                continue
        lines.append(line)
    return "\n".join(lines).strip() + "\n"
