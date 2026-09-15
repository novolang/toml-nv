# Changelog

All notable changes to toml-nv are recorded here. The format is
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
package follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
with the pre-1.0 rule that a breaking change bumps the MINOR number.

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
