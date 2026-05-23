# Smart Workspace

The Smart Workspace is a separate product layer built on top of the existing NER engine.

It does **not** replace the current entity-extraction workflow. The original extractor remains available in the main Document Analysis tab.

## What it adds

- Document subtype classification
- Plain-language explanation
- Red-flag detection
- Action items and reminder clues
- Timeline extraction
- Basic relation extraction
- Grounded question answering with sentence citations
- Document comparison
- Search across saved workspace documents
- Collections for grouping saved records

## Main endpoints

- `POST /api/workspace/analyze`
- `POST /api/workspace/compare`
- `POST /api/workspace/question`
- `GET /api/workspace/search`
- `GET /api/workspace/documents`
- `GET /api/workspace/documents/{document_id}`

## Storage

Saved workspace documents use SQLite by default:

```dotenv
WORKSPACE_STORE_PATH=data/workspace.sqlite3
```

## Important note

This layer currently uses:

- the existing NER output
- heuristic subtype/risk/timeline logic
- grounded extractive Q&A

It does **not** retrain the original NER models, by design, so the current extraction behavior stays stable.
