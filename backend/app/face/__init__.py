"""Enrolled-only face recognition.

Recognizes ONLY people the user explicitly enrolled (a personal "who's this again?" memory aid). It has no
database of the public and cannot identify strangers — an unenrolled face always returns "unknown".

Pipeline mirrors the rest of the backend: a pluggable Embedder (Mock for tests/dev, InsightFace for real
CPU face embeddings) behind an interface, a SQLite store, cosine matching in pure Python.
"""
