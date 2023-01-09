# timezones

* Status: proposed
* Deciders: [Sander, Wouter, Arnaud, Bart]
* Date: 2023-01-09

Technical Story: [
    https://github.com/inmanta/inmanta-core/issues/2919,
    https://github.com/inmanta/inmanta-core/pull/2953,
    https://github.com/inmanta/inmanta-lsm/pull/621,
]

## Context and Problem Statement

How do we deal with timezones when it comes to datetime data? This data is passed in both directions over the API, stored at
various places in the database and manipulated throughout the code. Which invariants do we uphold with regards to explicit
timezone information for these datetime objects?

## Decision Drivers

1. Behavior should be consistent regardless of the timezone participating hosts (e.g. server, agent, web-console client) live in.
2. Timezone handling over the API is non-trivial: we need to present a clear contract to the end-user.
3. In the absence of timezone information, there is no single sane interpretation: explicit timezones improve clarity.

## Considered Options

1. Use UTC everywhere
2. Use timezone-aware datetimes everywhere
3. Support both timezone aware and naive timestamps as input, return naive timestamps. All naive timestamps are implicitly
    assumed to be in UTC. Internally both a naive and an aware representation are considered.
4. Like the previous (mixed) option but make new end-points (where backwards compatibility is irrelevant) timezone-aware only.

## Decision Outcome

Chosen option: option 3 with timezone-aware internal representation. Support both timezone aware and naive timestamps as input,
use timezone-naive timestamps in API return values. Internally, always use timezone-aware timestamps (objects are converted at
the API boundary). Any timezone-naive timestamps represent a timestamp in UTC.

Rationale: it is as explicit as we can make it (decision driver 3) without breaking backwards compatibility. In contrast to
option 4, it remains simple: a single contract that applies to all API endpoints.

Option 2 (fully timezone-aware) has a lot of merit and we may want to migrate to it at some point, though that would be a
breaking change.

### Positive Consequences

* Clear contract for the end-user
* Supports explicit API input
* Internally (once past the API boundary) datetimes become straightforward to work with: everything is timezone-aware and any
    complexities resulting from timezone operations are offloaded transparently to the datetime library.
* Backwards compatible
* Any remaining naive timestamps are now well defined to be in UTC

### Negative Consequences

* API output must remain timezone-naive
* Difference between aware/naive on the API boundary vs internally can be confusing

## Pros and Cons of the Options

### option 1: UTC everywhere

* Good, because it presents a clear contract for the end user (all timestamps are implicitly in UTC)
* Bad, because it doesn't allow for explicit timezones
* Good, because its semantics are simple and consistent
* Good, because it is backwards compatible

### option 2: timezone-aware everywhere

* Good, because it presents a clear contract for the end user
* Good, because it makes all timezones explicit, improving clarity
* Good, because its semantics are simple and consistent
* Bad, because it breaks backwards compatibility

### option 4: mixed with timezone-aware only for new endpoints.

* Good, because it presents a clear contract for the end user
* Good, because it makes timezones as explicit as we can make them without breaking backwards compatibility
* Good, because it is backwards compatible
* Bad, because it is more complex to maintain two different semantics for API endpoints
