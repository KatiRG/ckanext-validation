from frictionless import Check, errors
import hashlib

class strict_duplicate_row(Check):
    """
    Deterministic duplicate-row check: hashes the parsed RAW cell strings
    from the SAME row stream. No re-parsing; avoids typed None artifacts.
    """
    code = "strict-duplicate-row"
    Errors = [errors.DuplicateRowError]

    # Don't override __init__ (v5 minor versions differ on signature)

    def validate_row(self, row):
        if not hasattr(self, "_seen"):
            self._seen = {}

        # Use RAW cells (strings) — this matches what the report shows
        try:
            cells = tuple(row.cells)               # strings
        except Exception:
            cells = tuple(row.to_list(json=False)) # fallback (still strings)

        # Stable digest over strings
        digest = hashlib.sha256("|".join(cells).encode("utf-8")).hexdigest()

        prev = self._seen.get(digest)
        if prev:
            note = f'the same as row at position "{prev}"'
            yield errors.DuplicateRowError.from_row(row, note=note)
        else:
            # v5 has row_number (1-based)
            self._seen[digest] = getattr(row, "row_number", None) or 0