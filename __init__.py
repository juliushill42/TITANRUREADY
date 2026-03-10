models:
  llm: "gemini-3-preview"
  embeddings: "text-embedding-004"
storage:
  type: "neo4j"
  uri: "bolt://localhost:7687"
workflows: [create_communities, create_community_reports]
