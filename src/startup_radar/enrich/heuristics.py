"""Deterministic skill/tag extraction. No LLM required."""

from __future__ import annotations

import re

# canonical display name keyed by lowercase match token
KNOWN_SKILLS: dict[str, str] = {
    "typescript": "TypeScript",
    "javascript": "JavaScript",
    "react native": "React Native",
    "react": "React",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "express": "Express",
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "python": "Python",
    "golang": "Go",
    "rust": "Rust",
    "c++": "C++",
    "supabase": "Supabase",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mysql": "MySQL",
    "sqlite": "SQLite",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "prisma": "Prisma",
    "cloudflare": "Cloudflare Workers",
    "tailwind": "Tailwind CSS",
    "three.js": "Three.js",
    "threejs": "Three.js",
    "graphql": "GraphQL",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "aws": "AWS",
    "gcp": "GCP",
    "vercel": "Vercel",
    "langchain": "LangChain",
    "llm": "LLMs",
    "machine learning": "Machine Learning",
    "mqtt": "MQTT",
    "esp32": "ESP32",
    "iot": "IoT",
}


def _has(text: str, token: str) -> bool:
    pattern = r"(?<![\w.])" + re.escape(token) + r"(?!\w)"
    return re.search(pattern, text) is not None


def extract_tags(text: str) -> list[str]:
    """Return canonical skill names found in free text, in first-seen order."""
    lowered = text.lower()
    found: list[str] = []
    for token, canonical in KNOWN_SKILLS.items():
        if canonical in found:
            continue
        if _has(lowered, token):
            found.append(canonical)
    return found
