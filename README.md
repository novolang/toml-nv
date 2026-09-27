# toml-nv

TOML is a configuration file format designed to be easy for a person to
read and to map unambiguously onto a table of key-value pairs. Its
specification is [TOML 1.0.0](https://toml.io/en/v1.0.0), and this
package implements the whole of it for novo-lang: a typed value tree, a
parser that names the line and the column of every refusal, dotted-key
access, a writer, and an editing document that changes one value and
leaves the rest of a person's file alone. Its date arms are
[calendar-nv](https://novo-lang.org/packages/calendar-nv)'s civil types.

## What it is

A TOML document is a **table**: an ordered list of **pairs**, each a key
and a value. A `[header]` line opens a table and the pairs under it
belong to it. A `[[header]]` line appends to an **array of tables**. An
**inline table**, written `{ a = 1 }`, is the same thing spelled on one
line.

A **key** may be bare, quoted with `"` or quoted with `'`, and a
**dotted key** such as `a.b.c` names a path through nested tables. The
three spellings of one key are one key: `a.b`, `a."b"` and `"a".b` name
the same place.

TOML has ten kinds of value, and this package's `TomlValue` has one arm
for each.

| Kind | Example | Arm |
| --- | --- | --- |
| Table | `[server]`, `{ a = 1 }` | `TomlTable` |
| Array | `[1, "two", true]` | `TomlArray` |
| String | `"a"`, `'a'`, `"""a"""` | `TomlStr` |
| Integer | `8080`, `0xff`, `1_000` | `TomlInt` |
| Float | `1.5`, `inf`, `nan` | `TomlFloat` |
| Boolean | `true`, `false` | `TomlBool` |
| Offset date-time | `1979-05-27T07:32:00Z` | `TomlOffsetDateTime` |
| Local date-time | `1979-05-27T07:32:00` | `TomlLocalDateTime` |
| Local date | `1979-05-27` | `TomlLocalDate` |
| Local time | `07:32:00` | `TomlLocalTime` |

The four date and time arms carry calendar-nv's `CivilDateTime`,
`CivilDate` and `CivilTime`, so that a program comparing a timestamp
from a configuration file with a date from anywhere else holds one type
and not two. `TomlOffsetDateTime` carries the offset beside the civil
date-time, as minutes east of UTC: `+02:00` is 120, `-05:30` is -330
and `Z` is 0.

There are two ways to write a document back out. `tomlwrite` renders a
value tree and keeps nothing that was not in it, which is what a
program generating a file wants. `tomledit` is a **document** that
remembers its own bytes: parsing and rendering gives back the text it
was given, and `set` rewrites only the span the value occupied.

## Install

```
novo pkg add toml-nv
```

## Example

```novo
use tomlerror
use tomlkeys
use tomlread
use tomlnode
use tomledit

fn main() [io]
    let text = "# the service's own settings\n[server]\nport = 8080\n"

    // Parse the text into a value tree. A refusal carries the line and
    // the column of the byte a person has to go and fix.
    match tomlread.parse(text)
        Err(e)  => println(tomlerror.render(e, "config.toml"))
        Ok(doc) =>
            // A dotted path, in the same language the document uses.
            // The `??` supplies a default when the key is absent.
            println("${tomlkeys.opt_int(doc, "server.port") ?? 8080}")

    // Change one value in the file itself. Everything the editing
    // document does not touch comes back byte for byte, comment
    // included.
    match tomledit.parse(text)
        Err(e) => println(tomlerror.render(e, "config.toml"))
        Ok(d)  =>
            match tomledit.set(d, "server.port", TomlInt(9090))
                Err(e2)  => println(tomlerror.render(e2, "config.toml"))
                Ok(next) => println(tomledit.to_string(next))
```

The program prints `8080`, then the document with `port = 9090` and
its comment in place. For a string left open on line 4 at column 12,
`tomlerror.render(e, "config.toml")` produces
`config.toml:4:12: a string was never closed`, which is the shape an
editor's error list parses.

## What the package contains

| Module | Contents |
| --- | --- |
| `tomlnode` | The value tree: the ten arms, the pair, the type name, and equality over two trees. |
| `tomlread` | Reading: from a string, from bytes, from a stream, one value on its own, and a check that answers only the first fault. |
| `tomlkeys` | Dotted-key access: lookups, typed reads that answer a result, optional reads that answer nothing, and the edits over a value tree. |
| `tomlwrite` | Rendering a value tree, in two styles, with the key quoting and the value spelling exposed on their own. |
| `tomledit` | The editing document: parse, change one value, add or read a comment, ask where a key is, and render. |
| `tomlerror` | Every way a document can be refused, each with the line and the column, and the rendering of one. |

## How to choose an entry point

**`tomlread.parse` takes the whole document as text.** It answers a
value tree. This is the ordinary way in.

**`tomlread.read_all` takes a stream.** It is declared
`read_all<S: Read[e]>(src: S) -> Result<TomlValue, TomlError> [e]`, so
it costs the caller whatever the caller's stream costs: a file charges
`[io, fs]` and an in-memory buffer charges nothing.

**`tomlkeys` reads values out of a tree.** `int_at` and its siblings
answer a result, naming the path and the type that was there instead.
`opt_int` and its siblings answer nothing at all for an absent key,
which is the shape a default wants.

**`tomlwrite.to_string` generates a file.** The same tree always
produces the same bytes. Use it for a lock file, a manifest a scaffold
writes, a fixture.

**`tomledit` changes a file somebody else wrote.** Use it for anything
that edits a file a person maintains.

## The rules a user needs

1. **Use `tomledit` to change a file and `tomlwrite` to generate one.**
   The canonical writer keeps nothing it was not given, so a tool that
   reads a person's `novo.toml`, changes one version and writes it back
   through `tomlwrite` hands them a difference on every line with their
   comments gone.
2. **`tomledit.to_string` of `tomledit.parse` is the text it was
   given**, for every text that parses. `set` rewrites the span the
   value occupied and nothing else: the spacing around the `=`, the
   trailing comment and the blank lines all survive. A new key goes
   after the last key of its table, and a key two or more tables below
   the nearest existing one opens a new header at the end of the file.
3. **A `TomlValue` is a value and a `TomlEdit` is a document.** Two
   trees holding the same data are the same tree, and `tomlnode.equal`
   says so. Two files holding the same data with different comments are
   different files. They are two types because they obey two different
   laws.
4. **A table is an ordered list of pairs, not a map.** That is what
   keeps a document's order through a round trip, and it is what makes
   a duplicate key representable, which the specification requires a
   parser to refuse.
5. **A local date-time is not an offset date-time with a zero offset.**
   `Z` is a claim about UTC and no offset is a refusal to claim. They
   are different arms, `tomlkeys.offset_datetime_at` refuses a local
   one rather than supplying a zero, and a writer must never turn one
   into the other.
6. **An offset is a number of minutes, not a zone.** `…+02:00` says
   what the offset was, not which zone it came from, so nothing here
   answers a zone.
7. **An integer is signed and 64 bits.** TOML requires exactly that
   range, so a literal outside it is `BadInteger` at parse time rather
   than a wrapped value in the tree.
8. **`inf` and `nan` are floats, not errors.** TOML spells them `inf`,
   `+inf`, `-inf` and `nan`.
9. **`true` and `false` are the only booleans.** `True` and `yes` are
   `BadValue`.
10. **An array may hold values of different kinds.** TOML 1.0.0 dropped
    the same-type requirement.
11. **An inline table may not span a newline.** The specification
    forbids it outright, and `UnterminatedInline` is its own arm
    because people are surprised by that rule often enough.
12. **A parse is bounded by a nesting depth.** A recursive parser
    handed `[[[[[[…` refuses at a named depth with `TooDeep` rather
    than overflowing a stack. `tomlread.default_depth` is what `parse`
    uses and `parse_with_depth` is how an embedded caller chooses its
    own.
13. **The position in a fault is where the mistake is, not where it was
    noticed.** `UnterminatedString` reports the opening delimiter.
    `DuplicateKey` reports both the second definition and the line of
    the first.
14. **Three faults have no position, and answer `-1`.** `NoSuchKey`
    and `WrongType` are about the caller's expectation rather than the
    file, and `Transport` means the stream failed before a line was
    reached. `tomlwrite.check` reports a key defined twice in a tree
    as `DuplicateKey` with every position `-1`, because a tree has no
    lines.
15. **`tomlerror.message` does not include the position.**
    `tomlerror.line_of` and `col_of` are separate, so a caller renders
    `file:line:col: message` in whatever shape its own diagnostics
    have. `tomlerror.render` is that shape, already assembled.
16. **A string in the tree is the value and not the spelling.** The
    escapes are applied, a multi-line string's leading newline is
    removed and its line-ending backslashes are honoured. Which of the
    four string forms was used is `tomledit`'s business.
17. **The canonical writer never moves a key.** A table becomes a
    `[header]` only when no plain key follows it in its table, because
    a `key = value` line after a header would belong to the header's
    table. Otherwise it is written inline. `tomlwrite.to_string` of a
    parsed tree reads back as an equal tree.
18. **A path names tables and keys, never an array element.** `a.0` is
    the key `0` of the table `a`. A key inside an array of tables has
    no dotted path, so `tomledit` cannot set it and `tomlkeys.at` is the
    way to reach it in a tree.
19. **Nothing here opens a file.** The caller holds the text.
    `tomlread.read_all` takes a stream the caller opened, and carries
    its failure through as `Transport` with the host's own `IoError`
    inside, so a caller can still tell a timeout from a truncated file.
    A document given as bytes that are not UTF-8, or that hold a zero
    byte, is `UnexpectedByte` at that byte.

## What is not included

- **Any input or output.** See rule 19.
- **Serialization of novo-lang structs.**
  [serde-nv](https://novo-lang.org/packages/serde-nv) is where that
  belongs.
- **Tree editing beyond `set`, `remove` and the comment pair.** The
  rest of what a document-editing library offers is a tree editor with
  TOML attached.
- **Schemas.** Whether a document is the right shape is
  [schema-nv](https://novo-lang.org/packages/schema-nv)'s question.
- **A time zone.** See rule 6.

## Related packages

- [calendar-nv](https://novo-lang.org/packages/calendar-nv) supplies
  the civil date and time types the four date arms carry. Declaring
  dates of this package's own would have put two incompatible date
  types in one program.
- `std.toml` in the standard library is the toolchain's own manifest
  reader: it is how `novo` reads `novo.toml`, and it is the right size
  for that. It parses a subset onto the JSON value tree, its whole
  error channel is an optional, so a document that fails gives no
  reason and no position, and it is not available on the embedded tier.
  This package has the positions, the whole of TOML 1.0.0, a writer and
  no effects. The two are expected to agree on every document the
  subset covers, which is what makes `std.toml` a useful in-tree oracle
  for the implementation.
- [yaml-nv](https://novo-lang.org/packages/yaml-nv),
  [ini-nv](https://novo-lang.org/packages/ini-nv) and
  [dotenv-nv](https://novo-lang.org/packages/dotenv-nv) are the other
  configuration formats on the registry.
- [config-nv](https://novo-lang.org/packages/config-nv) stacks several
  sources of configuration in precedence order, a TOML file among them.

## Tests

```bash
novo test tests/tomlread_tests.nv     # the grammar, the refusals, the two round-trip laws
novo test tests/tomlkeys_tests.nv     # dotted paths and typed reads
novo test tests/tomlnode_tests.nv     # the tree and equality
novo test tests/tomlcover_tests.nv    # the rest of the public surface
novo test tests/tomledit_tests.nv     # what an edit changes and what it leaves alone
novo test tests/tomlwrite_tests.nv    # the shapes the canonical writer produces
novo test tests/edges_tests.nv        # every refusal's message, and the edges
novo test tests/vectors_tests.nv      # the 709 TOML 1.0.0 documents of toml-test
bash tests/toml_test.sh [checkout]    # toml-test against its own JSON, and tomllib
bash tests/coverage.sh                # line coverage over src/, merged across suites
```

The TOML 1.0.0 specification is the oracle, and
[toml-test](https://github.com/toml-lang/toml-test)'s corpus is the
vector set. `vectors_tests.nv` holds every document of its
`files-toml-1.0.0` list: the 208 a parser must accept, each with the
tree it must produce, and the 501 it must refuse. `tests/toml_test.sh`
runs the same documents against the upstream JSON files, number by
number and instant by instant, and checks three round trips for each
valid one: the canonical writer in both styles reads back an equal
tree, and the editing document renders the text unchanged. Where the
Python interpreter has `tomllib`, it is a second reader: it must accept
and refuse the same documents and read the same trees.

Rust's `toml` and `toml_edit` crates are the reference for the split
between the two writers, and Python's `tomllib` for the shape of the
reading API and for the rules about which table may be defined or
extended where.

## Licence

Apache-2.0. See `LICENSE`.

<!-- docs/writing-a-readme.md is the style guide for this page. -->
