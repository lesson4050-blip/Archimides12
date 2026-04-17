# Issue #1042: KeyError on anchor tags without href and missing URL stripping

**Bug description:**
When using `extract_links()` in `formatter.py`, the code crashes with a `KeyError` if it encounters an `<a>` tag that doesn't have an `href` attribute (like a simple named anchor `<a></a>`). Instead of crashing, it should just skip such tags.
Additionally, URLs extracted from `href` attributes should have leading and trailing whitespaces stripped before being returned, as valid URLs sometimes get formatted with spaces.

**Steps to reproduce:**
Run `extract_links('<a>No link</a><a href=" http://example.com/ ">Example</a>')`

**Expected behavior:**
It should return `['http://example.com/']`.

**Actual behavior:**
It raises `KeyError: "Anchor tag is missing an 'href' attribute"`.
