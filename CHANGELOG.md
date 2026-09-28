# Changelog

All notable changes to toml-nv are recorded here. The format is
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
package follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
with the pre-1.0 rule that a breaking change bumps the MINOR number.

## 0.1.1 — 2026-09-28

The package builds beside a program, or another package, that declares
a variant with the same name as one of `TomlError`'s.  No signature and
no answer changed.

- Four modules built `TomlError` values with bare constructors such as
  `NoSuchKey(...)` without importing the enum.  A bare constructor that
  its own file neither declares nor imports is resolved across the whole
  build (SPEC § 9.4).  A build that also held yaml-nv, whose `YamlError`
  declares `NoSuchKey` and `WrongType`, was then refused with E2031
  inside toml-nv's source; config-nv is such a build.  `tomledit`,
  `tomlkeys`, `tomlparse` and `tomlwrite` now import the enum by name,
  `use tomlerror.{ TomlError }`.
- The change was checked with a suite that declares an enum repeating
  every variant name of the package's enums: before it, 56 constructor
  sites were refused, and after it none.  That suite is not shipped.
  Under `novo test`, an enum in a test file that repeats a package
  enum's variant names makes the package's values leak when they are
  dropped, even with identical payloads.  It is a toolchain defect, and
  the suite lands when it is fixed.
- A new case in `tests/tomlcover_tests.nv` reads from a stream that
  fails, and asserts `Transport` with the stream's fault.  It covers
  the one line of `src/` the 0.1.0 suites left unmeasured.

## 0.1.0 — 2026-09-27

The first implementation of the interface published as 0.0.1: TOML
1.0.0 read with a position on every refusal, dotted-path access, a
canonical writer, and an editing document that keeps a file's bytes.

### Behaviour the interface left open

- The parser accepts all 208 valid documents of toml-test's TOML 1.0.0
  corpus and refuses all 501 invalid ones.  Which table may be defined
  or extended where follows Python's `tomllib`.
- A dotted key that reaches into a table a header defined, and a header
  that defines a table a dotted key made, are `DuplicateKey`, with the
  line the table was first defined on.
- `parse_bytes` refuses a zero byte and any byte that is not UTF-8 as
  `UnexpectedByte` at that byte; `parse` checks UTF-8 too.
- A fraction of a second finer than a nanosecond is truncated.
- `tomlwrite` keeps every key where the tree has it.  A table becomes a
  header only when no plain key follows it in its table, and is written
  inline otherwise, so a parsed tree written and read back is equal to
  itself.  A float always carries a point or an exponent.
- `tomlwrite.check` reports a key defined twice anywhere in a tree,
  inside arrays too.
- `tomledit.set` adds a new key after the last key of its section, into
  the section whose dotted keys made its table, or before an inline
  table's `}`; a key two or more tables below the nearest existing one
  opens a header at the end.  It refuses, as `WrongType`, a path that
  names a table written as a header or passes through an array of
  tables, which have no single span.  `tomledit.remove` refuses a
  header's table the same way.
- `TomlError.message` names the rule the document broke, without the
  position; `tomlerror.render` adds `file:line:col`.
- `tomlnode.equal` counts two floats that are not numbers as equal, so
  a document holding `nan` equals itself after a round trip.
- The parser lives in a package-internal module, `tomlparse`, shared by
  `tomlread` and `tomledit`.

### Dependencies and toolchain

- calendar-nv `^0.2.0`, its first implemented release.
- The toolchain floor is 0.13.0. The bodies are written for it and use
  no workaround: `tomlnode.equal` compares the scalar and date-time arms
  with `==`, `tomlkeys.child` answers from inside the loop that finds
  the key, and `read_all` returns a stream failure from inside its
  read loop.

### Tests

- `vectors_tests.nv` holds every TOML 1.0.0 document of toml-test.
  `tests/toml_test.sh` runs the corpus against its own JSON files and
  against Python's `tomllib`, with the writer and editor round trips.
- `tomledit_tests.nv`, `tomlwrite_tests.nv` and `edges_tests.nv` cover
  the edits, the layouts and every refusal; `tests/coverage.sh` reports
  100% of the lines of `src/`.

## 0.0.4 — 2026-09-15

README rewritten to the package README style guide (docs/writing-a-readme.md); no change to the interface.

## 0.0.3 — 2026-09-10

- **Toolchain floor is 0.8.9**: the bodies and signatures use what 0.8.9 added (`todo()`, a bound effect parameter, the four layers), and the manifest says so instead of letting an older toolchain fail on an undefined function.  No signature changed.

## 0.0.2 — 2026-09-09

- **Dependencies are registry ranges**, not paths: the interface release 0.0.1 shipped a manifest whose dependencies pointed at sibling directories that exist only in the monorepo, so a consumer resolved the closure and then could not load the dependency.  No signature changed.

## [0.0.1] — 2026-09-09

**The interface, published before anyone implements it.** Every public
type and function carries its full signature, its effect row and its
doc comment; every body is `todo()`; the release is recorded
`implemented = false`.

### Added

- `tomlnode` — `TomlValue` with all ten of TOML's forms, `TomlPair` as
  an ordered table entry, and `TomlType` for naming an arm in a
  message. A table is an ordered list of pairs and not a map, so that
  a document read and written back keeps its order and so that a
  duplicate key stays representable — the specification requires
  refusing it, which a map could not.
- The four date arms carry calendar-nv's `CivilDate`, `CivilTime` and
  `CivilDateTime` rather than types of this package's own, so a
  timestamp out of a config file and a date from anywhere else are one
  type. An offset date-time carries minutes east of UTC beside the
  civil parts; a local date-time is a distinct arm and not an offset of
  zero.
- `tomlread` — `parse`, `parse_bytes`, `parse_value` and `check`, each
  refusing with a line and a byte column. Nesting is bounded at a named
  depth rather than overflowing a stack, and `parse_with_depth` makes
  the bound the caller's. `read_all<S: Read[e]>` is the one function
  that meets a stream, charged whatever the caller's impl supplies
  (SPEC § 5.6). There is deliberately no feed-and-drain reader: a TOML
  document is not complete until its last line, so a chunk-at-a-time
  reader would buffer the whole document and lie about it in its type.
- `tomlkeys` — dotted-path access in TOML's own key language, in two
  channels: a `Result` form that tells `NoSuchKey` from `WrongType` for
  a required setting, and a `?T` form for an optional one. Plus `set`,
  `remove` and `merge` on the value tree, which is the arithmetic a
  layered configuration is built from.
- `tomlwrite` — the canonical writer and `TomlStyle`. The same tree
  always renders the same bytes; comments and spacing are not in the
  tree and do not come back.
- `tomledit` — the editing document, this package's load-bearing
  interface. `to_string(parse(s)!) == s` byte for byte, `set` rewrites
  one span and leaves the spacing and the trailing comment alone, and
  `is_unchanged` answers the question a tool actually has: do I have to
  write this file?
- `tomlerror` — sixteen reasons, each carrying the line and the byte
  column a person has to go and look at, or `-1` where there is no such
  place. `impl Error for TomlError` supplies `message`.

### Known

- `novo test` is red, and that is the release's expected state: every
  assertion in the API suite reaches `not implemented:
  toml-nv.<module>.<fn>`. Run it with `--isolate` for one verdict per
  test naming the function it stopped at.
