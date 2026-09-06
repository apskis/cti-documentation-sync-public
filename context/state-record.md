# The state record

`portfolio_state.md` lives with the documents it describes, not in this
repository, at:

```
<documentation>/_doc_sync/portfolio_state.md
```

It stays there for three reasons: it describes the portfolio rather than the
tooling, it is the artifact a colleague would look for beside the documents, and
it syncs with them through OneDrive.

The sync run reads it as the comparison baseline and rewrites it at the end.
It carries:

- the deliverable class inventory as of the last run
- the house branding standard
- a "Known drift" work list
- the document version table
- a run history table

If it is ever missing, do not invent one from file timestamps. Report that the
baseline is gone and rebuild it from the deliverables tree in a run that makes
no document edits, then let April confirm it before the next real sync.
