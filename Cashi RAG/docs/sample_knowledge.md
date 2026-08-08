# Cashi RAG – Sample Knowledge Base

## What is Cashi

Cashi is a local RAG system for financial analytics documentation and code. It indexes Markdown and Python files, then answers questions by retrieving the most relevant chunks.

## Metrics glossary

- **Real**: actual recorded spend for a period.
- **Plan**: budget target for the year.
- **Forecast**: expected year-end outcome.
- **IMOR**: non-performing loan ratio style indicator when used in credit contexts.
- **Variance vs Plan**: Real − Plan (positive spend over plan is typically flagged).

## How indexing works

1. Walk the project tree for `.md` and `.py` files.
2. Split Markdown by headings and Python by functions/classes.
3. Tokenize text and store term frequencies.
4. At query time, score chunks with a TF–IDF style ranking and return top matches.

## API

Use `python rag/server_api.py` to expose a simple HTTP endpoint for queries, or call `rag.query.ask("your question")` from Python.
