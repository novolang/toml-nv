# toml-nv

**Status: NOT IMPLEMENTED — interface only.**

Every public function below is published with its signature and its
effect row, and every body is `todo()`. Installing this package works;
calling it panics with `not implemented`.

## What this is

TOML 1.0.0, read and written by a package that performs nothing itself.
A typed value tree with all ten of TOML's forms in it, a parser that
names the line and the column of every refusal, dotted-key access in
the same language the document uses, and **two** writers: a canonical
one that preserves nothing, and an editing document that preserves
everything — comments, key order, spacing — so a tool can change one
value and hand a person's file back without a diff on every line.

It is for the program whose USER writes the file: a service reading its
own configuration, a CLI with a `--config`, an installer that has to
edit a manifest, an embedded build reading settings out of flash.

```
novo pkg add toml-nv
novo pkg build
novo test
```

## The one example that will work

```novo
use tomlread
use tomlkeys

fn port_of(text: Str) -> Result<Int, TomlError>
    let doc = tomlread.parse(text)!
    Ok(tomlkeys.opt_int(doc, "server.port") ?? 8080)
```

A malformed document stops with a `TomlError` that carries the line and
the column — `tomlerror.render(e, "config.toml")` produces
`config.toml:4:12: a basic string was never closed`, which is the form
an editor's error list parses. A document that is fine but has no
`server.port` gets the default, because that lookup used the `?T`
channel and said so.

## The layer, and why

`core` — no effects at all, on a package whose whole subject is a file.

That is not a contradiction, it is the design. A TOML document is a
string the caller already holds, and parsing it is arithmetic over its
bytes: nothing is opened, nothing is waited for, and the state the
parser carries is a few integers and a stack bounded at a named depth.
The host owns the file; this package owns the grammar. That is also
what lets a firmware read its own configuration out of flash, which
`std.toml` — not available at `@tier(embedded)` — cannot do.

The one function that meets a stream stays inside the budget by
**binding** its cost rather than spending one:

```novo
pub fn read_all<S: Read[e]>(src: S) -> Result<TomlValue, TomlError> [e]
```

`S: Read[e]` binds the effect parameter of the standard library's
`Read` trait and the clause uses it, so the row means *whatever the
impl behind `S` supplies*. A file charges its caller `[io, fs]`; an
in-memory buffer charges nothing; `toml-nv` is charged neither, because
the impl that supplies the effect is declared where the host is.

## The load-bearing interface

Two writers, and the split is the design:

```novo
pub fn to_string(v: TomlValue, style: TomlStyle) -> Result<Str, TomlError>  // tomlwrite
pub fn parse(text: Str) -> Result<TomlEdit, TomlError>                      // tomledit
pub fn set(d: TomlEdit, path: Str, value: TomlValue) -> Result<TomlEdit, TomlError>
pub fn to_string(d: TomlEdit) -> Str
```

`tomlwrite` renders a `TomlValue` and throws away everything that was
not in it. The same tree always produces the same bytes, which is
exactly what a program *generating* a file wants — a lock file, a
manifest a scaffold writes, a fixture.

It is exactly what a program *editing* a file must not use. A tool that
reads a person's `novo.toml`, changes one version number and writes it
back through the canonical writer hands them a diff touching every line
with their comments gone. So `TomlEdit` is a document that remembers
its own bytes: `to_string(parse(s)!) == s` for every `s` that parses,
and `set` rewrites the span the value occupied and nothing else — the
spacing around the `=` survives, the trailing comment survives, the
blank lines survive.

They are two types rather than one because they obey different laws. A
`TomlValue` is a value: two trees holding the same data *are* the same
tree, and `tomlnode.equal` says so. A `TomlEdit` is a document: two
files holding the same data with different comments are different
files. One type doing both would answer one of those questions and be
wrong about the other — and would make every consumer that just wants a
config value carry trivia it will never read, including the embedded
ones, where that is the difference between fitting and not.

## The dates come from calendar-nv

TOML has four date-time forms and this package declares none of them.
The arms carry [calendar-nv](../calendar-nv)'s civil types, so that a
program comparing a timestamp from a config file with a date it got
from anywhere else holds one type and not two:

| TOML form | example | arm | carries |
| --- | --- | --- | --- |
| offset date-time | `1979-05-27T07:32:00Z` | `TomlOffsetDateTime` | `civil.CivilDateTime` + `offset_min` |
| local date-time | `1979-05-27T07:32:00` | `TomlLocalDateTime` | `civil.CivilDateTime` |
| local date | `1979-05-27` | `TomlLocalDate` | `civil.CivilDate` |
| local time | `07:32:00` | `TomlLocalTime` | `civil.CivilTime` |

`offset_min` is minutes east of UTC — `+02:00` is `120`, `-05:30` is
`-330`, `Z` is `0`. It sits *beside* the civil date-time rather than
inside a zoned type because TOML's offset is a fixed number of minutes
and not a zone: `…+02:00` says what the offset was, not which zone it
came from, and a package that invented a zone would be inventing. That
is the same split `calendar-nv.parse_rfc3339` makes.

A local date-time is **not** an offset one with `offset_min = 0`. `Z`
is a claim about UTC and no offset is a refusal to claim; the two are
different arms, `tomlkeys.offset_datetime_at` refuses a local one
rather than supplying a zero, and a writer must never turn one into the
other.

## How this differs from `std.toml`

`std.toml` is the **toolchain's own manifest reader** — it is how `novo`
reads `novo.toml`, and it is the right size for that. It parses a
subset onto the JSON value tree: scalars, `[section]` headers with
dotted paths, inline arrays of homogeneous scalars. Its whole error
channel is `?T`, so a document that fails gives you `None` with no
reason and no position, and `read_file` folds "could not be read" and
"is not TOML" into that same `None`. It is not available at
`@tier(embedded)`.

`toml-nv` is **the library a program depends on**. The difference is
four things, and each of them is something an end user notices:

- **Positions.** Every refusal names the line and the byte column. A
  person who mistyped a quote on line 41 is told line 41.
- **The whole of TOML 1.0.0.** Dates, arrays of tables, inline tables,
  multi-line strings, heterogeneous arrays — none of which are in the
  subset.
- **Round trips.** `tomledit` gives a tool a way to write a file back
  without destroying it. Nothing in `std.toml` writes at all.
- **`core`.** No effects, so it builds for embedded and for wasm.

`std.toml` is not something this replaces so much as the
toolchain-internal case it grew out of, and the two are expected to
agree on every document the subset covers — which is what makes it a
useful in-tree oracle for the implementation.

## The reference implementation

Rust's `toml` and `toml_edit` crates, and the split between them is the
one this package makes with `tomlwrite` and `tomledit` — `toml_edit`
exists because `toml` destroys a document it round-trips, and that
lesson is worth taking whole rather than learning again. Python's
`tomllib` for the shape of the reading API and for its insistence that
a library parses and does not open files. The TOML 1.0.0 specification
is the oracle, `toml-test`'s corpus is the vector set the implementation
will be measured against, and `std.toml` is the in-tree reference for
the subset both cover.

Deliberately not ported: `toml`'s Serde integration — `serde-nv` is
where that belongs, and a `toml-nv` that knew about it would be two
packages; `toml_edit`'s document-mutation API beyond `set`, `remove`
and the comment pair, because the rest of it is a tree-editing library
with TOML attached; and any notion of a schema, which is `schema-nv`.

## Status

Every function is `todo()`. `novo test --isolate` runs the API suite
and every assertion reaches `not implemented: toml-nv.<module>.<fn>`,
which is the expected result until the bodies land and is what makes
the suite a description of the interface rather than of nothing.

| module | public types | functions | implemented |
| --- | --- | --- | --- |
| `tomlnode` | `TomlValue`, `TomlPair`, `TomlType` | 8 | no |
| `tomlerror` | `TomlError` (+ `impl Error`) | 3 | no |
| `tomlread` | — | 8 | no |
| `tomlkeys` | — | 25 | no |
| `tomlwrite` | `TomlStyle` | 7 | no |
| `tomledit` | `TomlEdit` | 11 | no |

Seven public types, 61 public functions and one trait impl.

## Licence

Apache-2.0.
